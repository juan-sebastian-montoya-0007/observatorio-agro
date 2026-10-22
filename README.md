# EVA Explorer

EVA Explorer transforma las Evaluaciones Agropecuarias Municipales de Colombia en una plataforma pública de consulta y análisis trazable.

## Requisitos

- Docker Desktop con Docker Compose.
- Node.js 24 LTS y pnpm 11 para ejecución local del frontend.
- Python 3.13 y uv para ejecución local del backend.

## Inicio local

1. Copie `.env.example` como `.env` y cambie las credenciales locales.
2. Ejecute `docker compose up --build`.
3. Abra `http://localhost:3000`; la API queda en `http://localhost:8000`.

El archivo fuente EVA no se versiona. La importación se documentará junto con el comando del backend en el Corte 1.
