# Observatorio Agro

Observatorio Agro transforma datos agropecuarios de Colombia en una plataforma pública de consulta y análisis trazable.

Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA.

## Requisitos

- Docker Desktop con Docker Compose.
- Node.js 24 LTS y pnpm 11 para ejecución local del frontend.
- Python 3.13 y uv para ejecución local del backend.

## Inicio local

1. Copie `.env.example` como `.env` y ajuste únicamente sus credenciales locales.
2. Levante PostgreSQL: `docker compose up -d db`.
3. Aplique las migraciones e importe el libro fuente desde el backend nativo.
4. Ejecute `docker compose up --build -d`.
5. Abra `http://localhost:3000`; la API queda en `http://localhost:8000`.

El archivo fuente no se versiona ni se modifica. Los comandos completos de PowerShell para validar su hash, importarlo, comprobar la idempotencia y ejecutar las pruebas están en [Verificación del Corte 1](docs/corte-1-verification.md).

## Estado del Corte 1

## Asistente de datos

El botón **Asistente IA**, abajo a la derecha, abre el chat en las tres páginas.
Permite consultar rankings, resúmenes y evolución de áreas, producción y rendimiento.
Ejemplo: «¿Dónde se cultiva más café?» (área cosechada, departamentos, último año disponible).
Las cifras se calculan en PostgreSQL; Ollama interpreta una acción validada de lectura.
No ofrece información de precios, clima ni áreas todavía cosechables.
No requiere clave ni créditos. El historial vive en memoria y se borra al recargar;
se usan como máximo seis mensajes recientes para interpretar seguimientos.
Límites: preguntas de 500 caracteres, cuerpo de 24 KB, 10 peticiones por IP y
60 globales por minuto. Antes de publicar en Internet, agregar autenticación y
un limitador compartido entre réplicas. Ver instalación local más abajo.
### Estado histórico del Corte 1

El Resumen General está conectado a datos publicados e incluye filtros persistentes en la URL, KPIs con metodología contextual, serie histórica, rankings y distribución por cultivo. Los demás módulos aparecen señalados para cortes posteriores y no simulan funcionalidad.

La carga aprobada contiene 166.733 hechos, concilia 151.312 filas de control y conserva las advertencias de calidad de la fuente. El Dashboard nunca incorpora cifras agrícolas de ejemplo.

## Chatbot local con Ollama
El proveedor predeterminado es Ollama (Qwen3 4B); no utiliza la clave de OpenAI ni recurre a ese proveedor automáticamente. El modelo interpreta una acción JSON validada y PostgreSQL calcula todas las cifras.

```powershell
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:4b
docker compose up --build -d
```

La configuración actual utiliza la GPU NVIDIA del equipo mediante `gpus: all`. Para un equipo sin NVIDIA, retirar esa línea permite ejecutar en CPU (más lento). El modelo se conserva en `eva_ollama_data`; no eliminar ese volumen ni el volumen de PostgreSQL. Ollama no publica puertos al exterior y tiene funciones cloud desactivadas.

Primera descarga: requiere Internet y varios GB libres. Las consultas posteriores son locales. El primer uso puede demorar mientras carga el modelo; el cliente espera hasta 190 segundos. Con backend fuera de Docker, iniciar Ollama local y configurar `OLLAMA_BASE_URL=http://localhost:11434`.

Errores `LOCAL_AI_UNAVAILABLE`: comprobar `docker compose ps`, `docker compose exec ollama ollama list` y `docker compose logs --tail 30 ollama`. No se requiere saldo ni API key. `ASSISTANT_PROVIDER=openai` es una opción explícita de compatibilidad del backend, no un fallback; si se activa debe actualizarse también el aviso del widget sobre dónde se procesan las preguntas.


## Enlace temporal de revisión
La web utiliza rutas `/api/v1` del mismo dominio; Next las redirige al backend interno. Para aplicar: `docker compose up --build -d`.

Con cloudflared instalado, ejecutar desde PowerShell en la raíz:
```powershell
./scripts/start-review-tunnel.ps1
Get-Content ./tmp/review-tunnel.err.log -Tail 20
```
Compartir la URL HTTPS `trycloudflare.com`. Es pública para quien tenga el enlace, temporal y requiere PC, Docker y cloudflared encendidos. No incorpora Cloudflare Access; para revisiones restringidas configurar cuenta, dominio y política de acceso.

Detener solo el enlace (conservando la aplicación y datos):
```powershell
./scripts/stop-review-tunnel.ps1
```
Al reiniciar el túnel cambia la URL. Los puertos 5432 y 8000 están vinculados a localhost; Ollama no publica puertos. La API se ofrece mediante el proxy de la web; sus límites de uso siguen activos. La carga inicial del chatbot puede tardar y está sujeta al tiempo máximo de Cloudflare.
