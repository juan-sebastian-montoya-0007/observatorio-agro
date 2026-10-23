# EVA Explorer

EVA Explorer transforma las Evaluaciones Agropecuarias Municipales de Colombia en una plataforma pública de consulta y análisis trazable.

## Requisitos

- Docker Desktop con Docker Compose.
- Node.js 24 LTS y pnpm 11 para ejecución local del frontend.
- Python 3.13 y uv para ejecución local del backend.

## Inicio local

1. Copie `.env.example` como `.env` y ajuste únicamente sus credenciales locales.
2. Levante PostgreSQL: `docker compose up -d db`.
3. Aplique las migraciones e importe una fuente EVA desde el backend nativo.
4. Ejecute `docker compose up --build -d`.
5. Abra `http://localhost:3000`; la API queda en `http://localhost:8000`.

El archivo fuente EVA no se versiona ni se modifica. Los comandos completos de PowerShell para validar su hash, importarlo, comprobar la idempotencia y ejecutar las pruebas están en [Verificación del Corte 1](docs/corte-1-verification.md).

## Estado del Corte 1

El Resumen General está conectado a datos publicados e incluye filtros persistentes en la URL, KPIs con metodología contextual, serie histórica, rankings y distribución por cultivo. Los demás módulos aparecen señalados para cortes posteriores y no simulan funcionalidad.

La carga aprobada contiene 166.733 hechos, concilia 151.312 filas de control y conserva las advertencias de calidad de la fuente. El Dashboard nunca incorpora cifras agrícolas de ejemplo.
