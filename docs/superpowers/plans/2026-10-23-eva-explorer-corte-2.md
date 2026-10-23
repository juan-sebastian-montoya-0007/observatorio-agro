# EVA Explorer Corte 2 — Consulta y distribución Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar consultas históricas paginadas y ordenables, exportaciones CSV/XLSX trazables, navegación funcional y un repositorio de fuentes conectado a la versión EVA publicada.

**Architecture:** El backend amplía el monolito modular existente con un contrato único de selección de registros reutilizado por detalle y exportaciones. El frontend mueve el armazón institucional a un layout compartido, conserva filtros en la URL y consume exclusivamente servicios tipados; ninguna vista carga el conjunto completo en el navegador.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, openpyxl, PostgreSQL/PostGIS, Next.js 16 App Router, React 19, TypeScript estricto, Lucide React, Vitest, pytest y Playwright.

**Spec:** `docs/superpowers/specs/2026-10-22-eva-explorer-design.md`

**Supersession:** Product naming and standalone Geovisor requirements are superseded by `docs/superpowers/specs/2026-10-23-observatorio-agro-rebrand-chat-design.md`. The current product is Observatorio Agro, Geovisor is omitted from navigation, and cartography is implemented inside Resumen General by `docs/superpowers/plans/2026-10-23-observatorio-agro-mapa-resumen.md`.

## Global Constraints

- Trabajar sobre la arquitectura y la base real verificadas en el Corte 1; no introducir datos ficticios ni modificar el Excel fuente.
- `BasePagina` continúa siendo la única tabla factual y la versión publicada más reciente es el ámbito de consulta.
- Los códigos DIVIPOLA se exponen como texto de dos y cinco caracteres y conservan ceros iniciales en JSON, CSV y Excel.
- `AGRICULTURAL_YEAR` evita doble conteo; `SOURCE` requiere un tipo de periodo explícito (`ANNUAL`, `SEMESTER_A` o `SEMESTER_B`).
- El rendimiento agregado continúa siendo `SUM(production_t) / SUM(harvested_area_ha)`; el detalle expone también el rendimiento reportado sin sustituir la métrica agregada.
- Paginación, búsqueda y ordenamiento ocurren en PostgreSQL. El frontend nunca solicita todos los hechos para paginarlos localmente.
- CSV se transmite por filas; XLSX usa `openpyxl` en modo `write_only` y un temporal que se elimina al terminar o fallar.
- Las exportaciones reutilizan exactamente los filtros, búsqueda y ordenamiento de la tabla.
- La procedencia no se inventa: enlace oficial EVA 2025 `https://upra.gov.co/es-co/eva/eva-2025`; términos no confirmados se muestran como no documentados.
- La interfaz permanece en español de Colombia, con unidades, carga, vacío, error y foco visible.
- Todo acceso HTTP del frontend vive en `frontend/src/services/`; los componentes no construyen URLs de backend.
- Implementar con TDD, ejecutar la suite completa relevante y crear un commit por tarea aprobada.

## Review Focus

- Modo `SOURCE` sin periodo: debe rechazarse antes de consultar para impedir sumar anual y semestres; prueba en Task 1.
- Ordenamiento empatado entre páginas: debe incluir desempate estable por ID y no repetir ni omitir filas; prueba en Task 2.
- Búsqueda combinada con filtros dependientes: debe mantener departamento/municipio y no escapar la lista permitida de columnas; prueba en Task 2.
- Exportación interrumpida o fallida: debe cerrar cursor/sesión y eliminar el temporal XLSX; prueba en Task 3.
- En navegación compacta/móvil cada enlace conserva nombre accesible y el panel cierra con Escape devolviendo foco; prueba en Task 5.

---

### Task 1: Endurecer periodo, unidades y metadatos analíticos

**Files:**
- Modify: `backend/app/schemas/filters.py`
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/repositories/agriculture.py`
- Modify: `backend/app/services/analytics.py`
- Modify: `backend/tests/schemas/test_filters.py`
- Modify: `backend/tests/repositories/test_agriculture.py`
- Modify: `backend/tests/api/test_agriculture.py`
- Modify: `frontend/src/types/filters.ts`
- Modify: `frontend/src/hooks/use-dashboard-filters.ts`
- Modify: `frontend/src/hooks/use-dashboard-filters.test.tsx`
- Modify: `frontend/src/components/dashboard/dashboard-filters.tsx`
- Modify: `frontend/src/services/agriculture.ts`
- Modify: `frontend/src/services/agriculture.test.ts`

**Interfaces:**
- Consumes: `PeriodType`, `PeriodMode`, `Indicator`, `AgricultureFilters`, respuestas analíticas existentes.
- Produces: `AgricultureFilters.period_type: PeriodType | None` (alias `period_type`), `indicator_unit(indicator: Indicator) -> str`, `ResponseMeta.filters: dict[str, object]`, filtro frontend `periodType?: "ANNUAL" | "SEMESTER_A" | "SEMESTER_B"`.

- [ ] **Step 1: Write failing schema and repository tests**

Probar que `SOURCE` sin `period_type` devuelve validación 422, que `SOURCE+SEMESTER_A` solo agrega ese grano, que `AGRICULTURAL_YEAR+period_type` se rechaza y que el valor predeterminado seguro es `AGRICULTURAL_YEAR`.

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend && uv run pytest tests/schemas/test_filters.py tests/repositories/test_agriculture.py tests/api/test_agriculture.py -v`

Expected: FAIL porque no existe `period_type` y el modo fuente todavía puede mezclar granos.

- [ ] **Step 3: Implement the minimal backend contract**

Añadir el periodo explícito, aplicar `Period.period_type == filters.period_type` en modo `SOURCE`, mapear unidades exactas (`ha`, `t`, `t/ha`) y serializar los filtros aplicados dentro de `meta`.

- [ ] **Step 4: Write and run failing frontend URL-state tests**

Probar que cambiar a `SOURCE` añade un periodo fuente válido, volver a año agrícola lo elimina, recargar conserva la selección y los servicios Summary/Series/Rankings envían `period_type` únicamente en modo fuente.

Run: `cd frontend && pnpm vitest run src/hooks/use-dashboard-filters.test.tsx src/services/agriculture.test.ts`

Expected: FAIL porque el tipo y el selector no existen.

- [ ] **Step 5: Implement the source-period selector and verify GREEN**

Run: `cd backend && uv run pytest tests/schemas/test_filters.py tests/repositories/test_agriculture.py tests/api/test_agriculture.py -v`

Run: `cd frontend && pnpm vitest run src/hooks/use-dashboard-filters.test.tsx src/services/agriculture.test.ts src/components/dashboard/dashboard.test.tsx`

Expected: PASS; el Dashboard no mezcla granularidades.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests frontend/src
git commit -m "fix: make source-period analytics explicit"
```

### Task 2: Registros paginados, búsqueda y ordenamiento permitidos

**Files:**
- Create: `backend/app/schemas/records.py`
- Modify: `backend/app/schemas/agriculture.py`
- Modify: `backend/app/repositories/agriculture.py`
- Modify: `backend/app/services/analytics.py`
- Modify: `backend/app/api/v1/agriculture.py`
- Create: `backend/tests/repositories/test_records.py`
- Create: `backend/tests/api/test_records.py`
- Modify: `backend/tests/api/test_openapi.py`

**Interfaces:**
- Consumes: filtros endurecidos de Task 1 y joins de `AgricultureRepository`.
- Produces: `RecordSortField`, `SortDirection`, `RecordSelectionQuery(AgricultureFilters)`, `RecordPageQuery(RecordSelectionQuery)`, `AgriculturalRecordOut`, `RecordPageOut`, `AgricultureRepository.records(query) -> RecordPage`, `GET /api/v1/agriculture/records`.

- [ ] **Step 1: Write failing repository tests**

Cubrir página/tamaño, total independiente del límite, búsqueda case-insensitive en departamento/municipio/cultivo, todos los filtros existentes, orden ascendente/descendente, desempate por ID y códigos con ceros.

- [ ] **Step 2: Verify repository RED**

Run: `cd backend && uv run pytest tests/repositories/test_records.py -v`

Expected: FAIL porque no existe el contrato de detalle.

- [ ] **Step 3: Implement record query and page contracts**

`page >= 1`, `1 <= page_size <= 100`, `sort_by` limitado al enum y `sort_direction` limitado a `asc|desc`. Seleccionar nombres y códigos territoriales, año/tipo de periodo, cultivo/variante/estado, métricas NUMERIC y procedencia de fila.

- [ ] **Step 4: Write failing API/OpenAPI tests**

Probar envelope, total/página/tamaño, 422 para sort inválido o filtros incompatibles y presencia de la ruta en OpenAPI.

- [ ] **Step 5: Implement `GET /agriculture/records` and verify GREEN**

Run: `cd backend && uv run pytest tests/repositories/test_records.py tests/api/test_records.py tests/api/test_openapi.py -v`

Expected: PASS con consultas deterministas y acotadas.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add paginated agricultural records API"
```

### Task 3: Exportaciones CSV y XLSX con el mismo contrato

**Files:**
- Create: `backend/app/services/exports.py`
- Create: `backend/app/api/v1/exports.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/repositories/agriculture.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/services/test_exports.py`
- Create: `backend/tests/api/test_exports.py`
- Modify: `backend/tests/api/test_health.py`
- Modify: `backend/tests/api/test_openapi.py`

**Interfaces:**
- Consumes: `RecordSelectionQuery`, orden permitido y proyección de Task 2.
- Produces: `AgricultureRepository.iter_records(selection, batch_size)`, `stream_csv(selection)`, `build_xlsx(selection) -> Path`, `GET /api/v1/exports/agriculture?format=csv|xlsx`.

- [ ] **Step 1: Write failing export-service tests**

Comprobar cabeceras, orden idéntico al detalle, códigos tratados como texto, decimales sin pérdida, límite predeterminado de `200000` filas, error estable `EXPORT_ROW_LIMIT_EXCEEDED` antes de iniciar la respuesta y ausencia de truncado silencioso.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest tests/services/test_exports.py -v`

Expected: FAIL porque no existe el servicio.

- [ ] **Step 3: Implement streaming CSV and write-only XLSX**

CSV usa un generador por lotes cuyo resultado SQL se cierra en `finally`; la sesión continúa siendo propiedad de la dependencia request-scoped de FastAPI. XLSX crea un libro `write_only`, aplica formato de texto a DIVIPOLA y guarda en un temporal fuera del repositorio; la transmisión usa un iterador con `finally` que elimina el archivo. Añadir una prueba ASGI que cancela el envío sin consumir el cuerpo completo, además de fallos durante construcción y transmisión, para verificar cierre de cursor y limpieza real.

- [ ] **Step 4: Write failing API tests and add router**

Probar `Content-Type`, `Content-Disposition`, filtros/orden, 422 para formato inválido, 413 con código estable al superar `200000`, y OpenAPI. Configurar CORS con `expose_headers=["Content-Disposition"]` y comprobar una petición con `Origin: http://localhost:3000`.

- [ ] **Step 5: Verify GREEN**

Run: `cd backend && uv run pytest tests/services/test_exports.py tests/api/test_exports.py tests/api/test_openapi.py -v`

Expected: PASS sin temporales residuales.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: export filtered EVA records"
```

### Task 4: Catálogo de procedencia completo

**Files:**
- Modify: `backend/app/schemas/catalog.py`
- Modify: `backend/app/repositories/catalog.py`
- Modify: `backend/app/repositories/imports.py`
- Modify: `backend/tests/api/test_catalog.py`
- Modify: `backend/tests/importer/test_import_service.py`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/services/catalog.ts`

**Interfaces:**
- Consumes: `Source`, `SourceVersion`, `ImportRun` y versión publicada.
- Produces: `SourceOut` con descripción, URL oficial, condiciones de reutilización opcionales, fecha, notas, variables, conteo factual y último resumen de importación.

- [ ] **Step 1: Write failing catalog/import tests**

Probar que una importación nueva registra la URL oficial verificada, que campos no verificados permanecen `null`, y que `/catalog/sources` expone cobertura, variables, conteo, hash y estado de procesamiento. Probar también un backfill sobre la versión ya publicada: actualiza solo metadatos de `Source`, sin cambiar hash, hechos, versión ni número de ejecuciones.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest tests/api/test_catalog.py tests/importer/test_import_service.py -v`

Expected: FAIL por contrato incompleto.

- [ ] **Step 3: Implement provenance projection without invented terms**

Usar la URL oficial EVA 2025 fijada en Global Constraints; derivar variables del esquema factual y conteos de la base. Mantener `reuse_terms=null` hasta disponer de una condición oficial verificable. Ejecutar el backfill idempotente de metadatos antes del retorno `ALREADY_IMPORTED`, preservando toda la carga existente.

- [ ] **Step 4: Update frontend types/services and verify GREEN**

Run: `cd backend && uv run pytest tests/api/test_catalog.py tests/importer/test_import_service.py -v`

Run: `cd frontend && pnpm vitest run src/services/agriculture.test.ts src/components/dashboard/dashboard.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests frontend/src/types frontend/src/services
git commit -m "feat: expose complete EVA source provenance"
```

### Task 5: Armazón navegable, activo y responsive

**Files:**
- Create: `frontend/src/app/(platform)/layout.tsx`
- Move: `frontend/src/app/page.tsx` to `frontend/src/app/(platform)/page.tsx`
- Move: `frontend/src/app/page.test.tsx` to `frontend/src/app/(platform)/page.test.tsx`
- Create: `frontend/src/app/(platform)/comparador/page.tsx`
- Create: `frontend/src/app/(platform)/acerca/page.tsx`
- Modify: `frontend/src/components/layout/app-shell.tsx`
- Modify: `frontend/src/components/layout/sidebar.tsx`
- Modify: `frontend/src/components/layout/header.tsx`
- Modify: `frontend/src/components/layout/app-shell.test.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: query string de filtros compartidos y App Router.
- Produces: cinco enlaces reales, `aria-current="page"`, títulos por ruta, botón de contraer escritorio, panel móvil con control de foco/Escape y enlaces que conservan filtros aplicables.

- [ ] **Step 1: Write failing navigation/accessibility tests**

Probar nombres accesibles en modo compacto, ruta activa, conservación de query, apertura/cierre móvil, Escape y retorno de foco. Probar que las cinco rutas resuelven: Consulta y Repositorio se completan en este corte; Comparador y Acerca muestran un estado de disponibilidad explícito hasta cortes posteriores, sin controles simulados. Geovisor no aparece ni se crea como ruta independiente.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm vitest run src/components/layout/app-shell.test.tsx`

Expected: FAIL porque cinco módulos son `div` deshabilitados y no existe menú móvil.

- [ ] **Step 3: Implement shared platform layout and navigation**

El layout raíz conserva metadatos; `(platform)/layout.tsx` monta una sola vez `AppShell`. Sidebar y Header son clientes solo donde necesitan pathname/estado. Separar las pruebas de página y layout según sus nuevas responsabilidades.

- [ ] **Step 4: Verify GREEN and build**

Run: `cd frontend && pnpm vitest run src/components/layout/app-shell.test.tsx src/app/page.test.tsx`

Run: `cd frontend && pnpm lint && pnpm build`

Expected: PASS y cinco rutas resolubles aunque las vistas de datos lleguen en Tasks 6–7 y cortes posteriores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app frontend/src/components/layout frontend/src/app/globals.css
git commit -m "feat: enable responsive platform navigation"
```

### Task 6: Consultas avanzadas conectadas al backend

**Files:**
- Create: `frontend/src/app/(platform)/consultas/page.tsx`
- Create: `frontend/src/components/consultas/consulta-page.tsx`
- Create: `frontend/src/components/consultas/consulta-filters.tsx`
- Create: `frontend/src/components/consultas/records-table.tsx`
- Create: `frontend/src/components/consultas/column-selector.tsx`
- Create: `frontend/src/components/consultas/consulta-page.test.tsx`
- Create: `frontend/src/services/records.ts`
- Create: `frontend/src/services/records.test.ts`
- Create: `frontend/src/hooks/use-record-query.ts`
- Create: `frontend/src/hooks/use-record-query.test.tsx`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/types/filters.ts`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: `/agriculture/records`, `/exports/agriculture`, catálogos y serialización compartida de filtros.
- Produces: `RecordQueryFilters` con `yearFrom`, `yearTo`, filtros territoriales/agrícolas, `periodMode` y `periodType`; tabla paginada del servidor, búsqueda, orden, selección de columnas, total, descarga CSV/XLSX y estados accesibles.

- [ ] **Step 1: Write failing service and URL-state tests**

Probar que filtros, búsqueda, página, tamaño y orden se serializan una vez; una mutación de filtro vuelve a página 1; las URLs de descarga reutilizan la misma selección. Fijar estas reglas: cambiar departamento borra municipio; cambiar cultivo borra variante; `yearFrom <= yearTo`; Dashboard → Consulta convierte `year` en ambos extremos; Consulta → Dashboard usa `yearTo` como año visible y conserva territorio/cultivo/modo compatibles.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm vitest run src/services/records.test.ts src/hooks/use-record-query.test.tsx`

Expected: FAIL porque no existen los contratos.

- [ ] **Step 3: Implement typed record and export services**

Generalizar la serialización existente sin duplicar URLs en componentes. Las descargas se inician desde una función de servicio con nombre de archivo del encabezado.

- [ ] **Step 4: Write failing component tests**

Cubrir carga, datos, vacío contextual, error/reintento, orden, paginación, columnas, total y acciones CSV/XLSX con nombres accesibles.

- [ ] **Step 5: Implement `/consultas` and verify GREEN**

Run: `cd frontend && pnpm vitest run src/services/records.test.ts src/hooks/use-record-query.test.tsx src/components/consultas/consulta-page.test.tsx`

Expected: PASS; ninguna paginación local del dataset.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add advanced agricultural queries"
```

### Task 7: Repositorio de fuentes y versiones

**Files:**
- Create: `frontend/src/app/(platform)/repositorio/page.tsx`
- Create: `frontend/src/components/repositorio/source-repository.tsx`
- Create: `frontend/src/components/repositorio/source-repository.test.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: catálogo ampliado de Task 4.
- Produces: catálogo público con procedencia, cobertura, variables, versión, hash abreviado y copiable, estado de procesamiento, enlace oficial y estado explícito de reutilización.

- [ ] **Step 1: Write failing repository-page tests**

Probar datos reales del envelope, URL oficial, ausencia explícita de licencia no verificada, fecha/cobertura, estado vacío y error recuperable.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm vitest run src/components/repositorio/source-repository.test.tsx`

Expected: FAIL porque la página no existe.

- [ ] **Step 3: Implement the repository view**

No ofrecer descarga del archivo original almacenado localmente; enlazar la página oficial. La descarga procesada se realiza desde Consulta y declara filtros/procedencia.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && pnpm vitest run src/components/repositorio/source-repository.test.tsx`

Run: `cd frontend && pnpm lint && pnpm build`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add EVA source repository"
```

### Task 8: Verificación vertical del Corte 2

**Files:**
- Modify: `frontend/e2e/dashboard.spec.ts`
- Create: `frontend/e2e/queries.spec.ts`
- Create: `docs/corte-2-verification.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: aplicación Compose con la fuente real importada.
- Produces: recorrido Dashboard → Consulta → orden/página → CSV/XLSX → Repositorio, guía reproducible y estado documentado.

- [ ] **Step 1: Write failing E2E flows**

Comprobar navegación con filtros conservados y conversión de rango, resultado real contrastado con API, cambio de orden/página, descarga CSV y XLSX con códigos intactos, catálogo de fuente y menú móvil por teclado.

- [ ] **Step 2: Verify RED before completing any missing integration**

Run: `cd frontend && pnpm exec playwright test e2e/queries.spec.ts`

Expected: FAIL si queda cualquier unión o descarga pendiente.

- [ ] **Step 3: Complete only integration gaps exposed by E2E**

No añadir funcionalidad nueva; corregir enlaces, contratos o estados necesarios para el recorrido aprobado.

- [ ] **Step 4: Run complete verification**

Run: `cd backend && uv run ruff check . && uv run pytest -m 'not full_source' -v`

Run: `cd frontend && pnpm lint && pnpm vitest run && pnpm build && pnpm exec playwright test`

Antes del E2E aplicar migraciones, importar o reutilizar la fuente aprobada y verificar PostgreSQL. Después ejecutar por separado `docker compose up --build -d` y `docker compose ps`; Playwright reutiliza únicamente ese stack recién reconstruido.

Expected: suites y build PASS; `db`, `backend` y `frontend` saludables.

- [ ] **Step 5: Document exact Windows commands and source immutability**

La guía reutiliza la restauración segura de `DATABASE_URL`, comprueba API con consulta real y conserva el hash SHA-256 aprobado del Excel.

- [ ] **Step 6: Commit**

```bash
git add frontend/e2e docs README.md
git commit -m "test: verify EVA Explorer corte 2 end to end"
```

## Self-Review

- Spec coverage: este plan cubre Corte 2 — registros, filtros dependientes, búsqueda, paginación, ordenamiento, CSV/XLSX, navegación y repositorio. Comparador, geovisor, Acerca y endurecimiento global permanecen en los planes de Corte 3 y 4.
- Step scan: cada tarea contiene un ciclo RED/GREEN, un entregable aislado y un commit revisable.
- Type consistency: Task 1 fija filtros; Task 2 produce `RecordSelectionQuery`/`RecordPageQuery`; Task 3 reutiliza selección; Tasks 4, 6 y 7 consumen contratos anteriores sin duplicarlos.
- Review Focus: cada uno de los cinco riesgos tiene una prueba asignada.
- Proportion: el plan fija interfaces y resultados observables sin transcribir implementaciones.
