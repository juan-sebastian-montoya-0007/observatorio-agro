# EVA Explorer — verificación reproducible del Corte 1

Esta guía ejecuta el flujo vertical en Windows PowerShell: valida el libro suministrado sin modificarlo, prepara la base, importa los datos, levanta la aplicación y corre las pruebas.

## 1. Prerrequisitos

- Docker Desktop con Docker Compose.
- Python 3.13 y `uv`.
- Node.js 24 LTS, Corepack y pnpm 11.
- Una copia local autorizada de `20260526_BaseAgricola20192025 (2).xlsx`.

Desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env
$source = 'C:\Users\User\Downloads\20260526_BaseAgricola20192025 (2).xlsx'
$expectedHash = '355E70A7A5B8F3CE76F26F97463F77C24D4C5E63ABD7B28C9B6395A1F65854B0'
$beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
if ($beforeHash -ne $expectedHash) { throw 'El libro no corresponde a la fuente aprobada.' }
```

La ruta es local y puede cambiarse. No copie el libro dentro del repositorio ni lo añada a Git.

## 2. Base de datos, migración e importación nativa

```powershell
docker compose up -d db

Push-Location backend
uv sync
$previousDatabaseUrl = $env:DATABASE_URL
try {
    $env:DATABASE_URL = 'postgresql+psycopg://eva:change-me@localhost:5432/eva_explorer'
    uv run alembic upgrade head
    uv run eva import --path $source

    # La segunda importación comprueba idempotencia sin cambiar de conexión.
    uv run eva import --path $source
}
finally {
    if ($null -eq $previousDatabaseUrl) {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    }
    else {
        $env:DATABASE_URL = $previousDatabaseUrl
    }
    Pop-Location
}
```

La primera ejecución debe informar:

- `status`: `IMPORTED`
- `read_count`: `166733`
- `inserted_count`: `166733`
- `reconciliation.page_rows`: `151312`
- `reconciliation.control_rows`: `151312`
- `reconciliation.passed`: `true`
- `warning_count`: al menos `13208`

La segunda importación incluida en el bloque debe devolver `reused: true` y no duplicar hechos. El bloque `finally` restaura `DATABASE_URL` antes de iniciar Docker, incluso si algún comando falla.

## 3. Arranque de la aplicación

```powershell
docker compose up --build -d
docker compose ps
```

Los servicios `db`, `backend` y `frontend` deben aparecer como `healthy`. Verifique las respuestas:

```powershell
(Invoke-WebRequest -UseBasicParsing http://localhost:3000).StatusCode
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/catalog/sources
```

La consulta de catálogo confirma además que el backend puede acceder a PostgreSQL; el endpoint de salud por sí solo no ejecuta una consulta de datos.

Abra:

- Dashboard: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

## 4. Prueba de aceptación con el libro completo

La prueba usa una base de pruebas separada y se omite si la variable de fuente no está definida.

```powershell
Push-Location backend
$env:EVA_SOURCE_XLSX = $source
$env:TEST_DATABASE_URL = 'postgresql+psycopg://eva:change-me@localhost:5432/eva_explorer_test'
uv run pytest -m full_source tests/acceptance/test_full_workbook.py -v
Pop-Location
```

Al finalizar, compruebe que el original permanece intacto:

```powershell
$afterHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
if ($afterHash -ne $beforeHash) { throw 'El archivo fuente cambió durante la verificación.' }
```

## 5. Suites automatizadas

Backend, excluyendo la prueba opt-in del libro completo:

```powershell
Push-Location backend
uv run ruff check .
uv run pytest -m 'not full_source' -v
Pop-Location
```

Frontend y flujo real de navegador:

```powershell
Push-Location frontend
corepack enable
pnpm install --frozen-lockfile
pnpm lint
pnpm vitest run
pnpm build
pnpm exec playwright install chromium
pnpm exec playwright test
Pop-Location
```

Playwright reutiliza la aplicación levantada y verifica una versión publicada visible, KPIs reales, filtros persistidos después de recargar y el estado sin resultados.

## 6. Comprobación del árbol de trabajo

```powershell
git status --short
```

No deben aparecer `.env`, libros `.xlsx`, `backend/data/raw/`, reportes de Playwright ni secretos. Esos elementos están excluidos por `.gitignore`.

## 7. Solución de problemas

- Si PostgreSQL todavía no está listo, espere a que `docker compose ps` muestre `db` como `healthy` y repita la migración.
- Si el puerto 5432, 8000 o 3000 está ocupado, detenga el proceso que lo usa antes de arrancar el stack.
- Si el Dashboard aparece vacío, confirme que la importación devolvió `IMPORTED` o `ALREADY_IMPORTED` y que la versión fuente quedó publicada.
- Si Playwright no encuentra Chromium, ejecute `pnpm exec playwright install chromium` dentro de `frontend`.
- Para inspeccionar un servicio use `docker compose logs db`, `docker compose logs backend` o `docker compose logs frontend`; no publique el contenido de `.env`.
