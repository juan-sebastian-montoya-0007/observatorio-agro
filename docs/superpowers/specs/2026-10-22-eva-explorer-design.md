# EVA Explorer 1.0 — Especificación de diseño

Fecha: 2026-10-22  
Estado: diseño aprobado para planificación  
Idioma del producto: español de Colombia

## 1. Objetivo

EVA Explorer será una plataforma pública de consulta, análisis, comparación y visualización territorial de las Evaluaciones Agropecuarias Municipales de Colombia. Transformará archivos oficiales en un producto web trazable, accesible y orientado a datos, sin presentar información ficticia como oficial.

La ruta `/` abrirá directamente el Resumen General. No habrá landing page, autenticación, funciones sociales, perfiles, notificaciones ni controles sin comportamiento real.

El MVP debe permitir:

- Consultar indicadores agrícolas por territorio, cultivo y periodo.
- Explorar registros históricos con paginación desde el servidor.
- Comparar periodos y territorios compatibles.
- Visualizar indicadores sobre cartografía oficial.
- Exportar resultados filtrados.
- Conocer la fuente, versión, metodología y limitaciones de cada cifra.
- Incorporar nuevas versiones y conjuntos sin reconstruir el sistema.

## 2. Alcance aprobado

### Módulos

1. Resumen General (`/`).
2. Geovisor Agropecuario (`/geovisor`).
3. Consultas Avanzadas (`/consultas`).
4. Comparador Histórico (`/comparador`).
5. Repositorio de Datos (`/repositorio`).
6. Acerca de EVA Explorer (`/acerca`).

### Fuera del MVP

- Autenticación o perfiles de usuario.
- Edición manual de cifras desde la interfaz.
- Carga pública de archivos.
- Redis, colas distribuidas o microservicios.
- Predicciones, recomendaciones o modelos de inteligencia artificial.
- Redistribución del Excel original sin verificar sus condiciones de reutilización.
- Uso de logos oficiales sin autorización.

## 3. Fuente agrícola analizada

Archivo de trabajo: `20260526_BaseAgricola20192025 (2).xlsx`  
SHA-256: `355E70A7A5B8F3CE76F26F97463F77C24D4C5E63ABD7B28C9B6395A1F65854B0`

El archivo original permanecerá intacto. No se añadirá a Git. El importador aceptará una ruta explícita o un archivo ubicado en `backend/data/raw/`, directorio ignorado por Git.

### 3.1 Hojas

`BasePagina` contiene 166.733 registros y 18 columnas. Es la fuente factual detallada. Su encabezado está en la fila 9 y conserva 195 desagregaciones de cultivo.

`BaseSIPRA` contiene 151.312 registros y 18 columnas. Es una agregación exacta de `BasePagina` al colapsar los códigos detallados de cultivo a 166 códigos base. Las sumas de área sembrada, área cosechada y producción coinciden entre ambas hojas. `BaseSIPRA` se utilizará para conciliación, no como una segunda tabla de hechos.

### 3.2 Cobertura y calidad observada

- Periodo: 2019–2025.
- Departamentos: 32.
- Códigos municipales: 1.103.
- Cultivos base: 166.
- Desagregaciones de cultivo: 195.
- Periodos fuente: 21 valores — anual, semestre A y semestre B para cada año.
- No se observaron celdas nulas en las 18 columnas de `BasePagina`.
- No se observaron métricas negativas ni filas completas duplicadas.
- La clave municipio, código detallado, año, periodo, desagregación y estado físico es única en `BasePagina`.
- En registros con área cosechada mayor que cero, el rendimiento informado coincide con producción dividida por área cosechada dentro de una tolerancia de 0,01 t/ha.
- Existen 13.208 registros donde el área cosechada supera el área sembrada. Se conservarán y se marcarán como advertencia, no como error fatal.
- Existen 20 series de plantas aromáticas con registros anuales y semestrales simultáneos. Sus cifras no son equivalentes; no deben sumarse entre granularidades.
- El código base de papa `10807` representa al menos dos nombres científicos. La especie o variante debe permanecer en la clave analítica.

### 3.3 Notas metodológicas de la fuente

- Para cultivos transitorios, desde 2022 área cosechada, producción y rendimiento corresponden a cosechas efectivas del periodo; en años anteriores corresponden a las siembras realizadas en el periodo.
- Los dos años más recientes son susceptibles de ajustes posteriores.
- El municipio Nuevo Belén de Bajirá, DIVIPOLA `27493`, aparece desde 2024.
- La procedencia declarada incluye EVA-UPRA y fuentes colaboradoras indicadas en el libro.

Estas notas se registrarán como metadatos visibles y alimentarán advertencias de comparación.

## 4. Arquitectura

EVA Explorer será un monorepositorio con tres unidades desplegables:

- `frontend/`: Next.js con App Router, React, TypeScript estricto y Tailwind CSS.
- `backend/`: FastAPI, Pydantic, SQLAlchemy 2 y Alembic.
- `database`: PostgreSQL con PostGIS.

Docker Compose levantará los tres servicios para desarrollo local en Windows. El backend podrá ejecutarse fuera de Docker contra la base de datos en contenedor para facilitar depuración.

La arquitectura de backend será un monolito modular:

```text
API routers → application services → repositories → SQLAlchemy/PostGIS
                       ↓
              statistical policies
```

Los routers validan HTTP. Los servicios aplican reglas de negocio y agregación. Los repositorios encapsulan SQL. Ninguna regla estadística dependerá de un componente visual.

### 4.1 Estructura prevista

```text
frontend/
  src/
    app/
    components/{layout,dashboard,geovisor,consultas,comparador,common}/
    services/
    hooks/
    types/
    utils/
    styles/
  public/
backend/
  app/
    api/v1/
    core/
    db/
    models/
    schemas/
    repositories/
    services/
    statistics/
  migrations/
  scripts/
  data/{raw,processed}/
  tests/
docs/
docker-compose.yml
.env.example
.gitignore
README.md
```

## 5. Modelo relacional

### 5.1 Procedencia

`source`

- Entidad publicadora, nombre, descripción, URL oficial y condiciones de reutilización.

`source_version`

- Fuente, etiqueta de versión, cobertura, fecha disponible, hash, nombre del archivo, notas y estado.
- El hash evita registrar dos veces el mismo archivo como versiones diferentes.

`import_run`

- Versión, inicio, fin, estado, conteos leídos/insertados/rechazados, resumen y versión del importador.

`import_issue`

- Ejecución, severidad, hoja, fila, campo, código estable y descripción.

### 5.2 Territorio

`department`

- Código DIVIPOLA de dos caracteres, nombre y vigencia.

`municipality`

- Código DIVIPOLA de cinco caracteres, departamento, nombre y vigencia.

`territorial_geometry`

- Nivel territorial, código DIVIPOLA, geometría PostGIS, SRID, versión, simplificación, fuente y licencia.
- Se obtendrá de una fuente oficial verificable del DANE. Si no puede verificarse la procedencia o licencia, el geovisor permanecerá en estado no disponible; no se sustituirá con geometría inventada.

### 5.3 Catálogo agrícola

`crop_group` y `crop_subgroup`

- Clasificaciones observadas en la fuente.

`crop`

- Código base, nombre, ciclo, grupo, subgrupo y clasificación general.

`crop_variant`

- Cultivo base, código detallado de fuente, etiqueta de desagregación y nombre científico.
- Permite que un cultivo base conserve especies o variedades diferentes.

`physical_state`

- Estado físico de producción, por ejemplo “En fresco” o “Grano seco”.

### 5.4 Tiempo y hechos

`period`

- Año, tipo `ANNUAL | SEMESTER_A | SEMESTER_B`, etiqueta original y orden cronológico.

`agricultural_record`

- Versión de fuente.
- Municipio.
- Variante de cultivo.
- Periodo.
- Estado físico.
- Área sembrada en hectáreas.
- Área cosechada en hectáreas.
- Producción en toneladas.
- Rendimiento informado en t/ha.
- Fila original y metadatos de trazabilidad.

La restricción única será:

```text
(source_version_id, municipality_id, crop_variant_id, period_id, physical_state_id)
```

Los códigos territoriales se almacenarán como texto para conservar ceros iniciales. Las métricas usarán `NUMERIC` con precisión suficiente para evitar pérdidas por redondeo.

## 6. Importación y validación

El ETL será un comando explícito del backend y seguirá estas etapas:

1. Calcular hash y registrar o localizar la versión.
2. Abrir el libro en modo de lectura.
3. Verificar nombres de hojas, encabezados y tipos esperados.
4. Leer `BasePagina` a una estructura temporal por lotes.
5. Normalizar espacios, códigos y catálogos sin alterar valores numéricos.
6. Resolver dimensiones y preparar hechos.
7. Validar claves, periodos, relaciones territoriales y rangos estructurales.
8. Insertar dentro de una transacción.
9. Agregar los hechos al nivel de `BaseSIPRA` y conciliar conteos y métricas.
10. Confirmar la transacción y publicar el resumen de importación.

Una incompatibilidad de esquema, clave duplicada, código territorial inválido o conciliación fallida cancelará la carga completa. Una cifra inusual, un área cosechada superior a la sembrada o una combinación temporal excepcional generará una advertencia conservando el dato.

Reimportar el mismo hash será idempotente: devolverá la ejecución existente o una respuesta de “ya importado”, sin crear hechos duplicados.

## 7. Reglas estadísticas

### 7.1 Métricas

- Área sembrada, área cosechada y producción son aditivas dentro de periodos compatibles.
- El rendimiento agregado es `SUM(producción) / SUM(área cosechada)`.
- Si el denominador es cero, el rendimiento es no disponible; no se devuelve cero por conveniencia.
- El rendimiento informado se conserva para auditoría y consultas de detalle.
- No se suman ni promedian rendimientos fila por fila.

### 7.2 Estados del dato

- `0`: valor real informado por la fuente.
- Ausente: no existe registro para la combinación consultada.
- No aplicable: la métrica no tiene sentido para el filtro o denominador.
- Advertido: valor conservado con una observación metodológica o de calidad.

### 7.3 Periodos

Las consultas fuente exponen por separado anual, semestre A y semestre B.

El modo “año agrícola” usa:

- Registros anuales para cultivos permanentes.
- Registros semestrales para cultivos transitorios.
- En las 20 series transitorias con granularidades superpuestas, los semestres tienen prioridad y el anual queda excluido de la agregación.
- No se suman simultáneamente registros anuales y semestrales de una misma serie.

Cuando solo exista uno de los dos semestres, la API declarará cobertura parcial en metadatos. La interfaz no ocultará esa limitación.

### 7.4 Comparaciones

- Los dos lados deben utilizar el mismo indicador, modo temporal, unidad y nivel territorial.
- Una comparación que cruza 2021–2022 para producción, área cosechada o rendimiento de transitorios mostrará una advertencia de cambio metodológico.
- La variación porcentual no se calcula cuando el valor base es cero o no disponible.
- Los rankings excluyen valores no disponibles, pero conservan ceros reales.

## 8. API REST

La API se versionará bajo `/api/v1`.

### 8.1 Endpoints

- `GET /agriculture/summary`
- `GET /agriculture/series`
- `GET /agriculture/rankings`
- `GET /agriculture/records`
- `GET /agriculture/comparison`
- `GET /agriculture/map-values`
- `GET /catalog/crops`
- `GET /catalog/periods`
- `GET /catalog/sources`
- `GET /geography/departments`
- `GET /geography/municipalities`
- `GET /geography/geometry`
- `GET /exports/agriculture`

### 8.2 Filtros comunes

- Año o rango de años.
- Periodo o modo temporal.
- Departamento.
- Municipio dependiente del departamento.
- Cultivo base o variante.
- Grupo, subgrupo y ciclo.
- Estado físico.
- Indicador.

La API recibe códigos estables, no nombres visibles.

### 8.3 Formato analítico

```json
{
  "data": {},
  "meta": {
    "filters": {},
    "unit": "t",
    "source_version": "..."
  },
  "coverage": {},
  "warnings": [],
  "methodology": {}
}
```

`records` usa paginación en PostgreSQL, ordenamiento con lista permitida y tamaño máximo configurable. Las exportaciones reutilizan el mismo objeto de filtros y ordenamiento. CSV se transmite por streaming; Excel se genera en modo de escritura incremental mediante un archivo temporal eliminado al terminar la respuesta.

Los errores incluyen código estable, mensaje comprensible, campos inválidos y detalles metodológicos aplicables. OpenAPI será parte de la verificación del backend.

## 9. Geovisor

MapLibre GL JS es la opción predeterminada. Las geometrías y los valores estadísticos viajarán por separado:

- Nivel nacional: geometría departamental simplificada.
- Departamento seleccionado: geometrías municipales del departamento.
- Cambio de indicador: solo actualiza valores, no descarga nuevamente polígonos.

El endpoint estadístico devuelve código DIVIPOLA, valor, unidad y estado del dato. El frontend une por código.

La escala de color se calcula con valores válidos del filtro actual. Cero, ausente y no aplicable tendrán estilos diferentes. El mapa ofrecerá leyenda, zoom, reinicio, selección territorial, contexto y navegación hacia la consulta completa.

## 10. Frontend y experiencia

La dirección visual aprobada es “Analítica institucional”.

### 10.1 Armazón

- Sidebar verde institucional expandible con seis rutas.
- Header blanco con sección activa, contexto territorial/temporal y enlace a fuentes.
- Fondo neutro, superficies blancas, bordes discretos y sombras moderadas.
- IBM Plex Sans, Inter o Source Sans 3, priorizando disponibilidad y legibilidad.
- Color reservado para navegación, estados, acciones y series de datos.
- Lucide React con tamaño y trazo uniformes.

En tablet la barra lateral se contrae. En móvil se convierte en un panel desplegable. No se elimina ninguna función esencial.

### 10.2 Estado de filtros

Los filtros compartidos se reflejan en parámetros de URL para permitir recarga, enlaces y navegación predecible. Un proveedor de contexto mantiene la selección territorial cuando la siguiente ruta puede aplicarla. Los componentes nunca construyen URLs de backend; consumen funciones tipadas en `services/`.

### 10.3 Módulos

Resumen General:

- Filtros horizontales compactos.
- Cuatro indicadores principales en la primera fila.
- Serie histórica y principales cultivos como visualizaciones dominantes.
- Ranking territorial y distribución por cultivo en una columna secundaria.
- Advertencias metodológicas contextuales debajo del contenido afectado.

Geovisor:

- Mapa protagonista.
- Controles compactos sobre el mapa.
- Tarjeta contextual lateral o flotante que no cubra el territorio.
- Cambio progresivo Colombia → departamento → municipio.

Consultas:

- Panel de filtros y tabla paginada como protagonistas.
- Selección de columnas, búsqueda, ordenamiento y exportación funcional.
- Conteo total y contexto de fuente visibles.

Comparador:

- Dos selectores territoriales o temporales claramente separados.
- Resumen de diferencias, líneas, barras agrupadas y tabla.
- Bloqueo o advertencia antes de representar comparaciones incompatibles.

Repositorio:

- Catálogo de fuentes, versiones, coberturas, variables, estado de procesamiento, licencia y enlace oficial.

Acerca de:

- Explica proyecto, EVA, metodología, fuentes y limitaciones.
- Distingue EVA Explorer de la UPRA y evita aparentar oficialidad.

### 10.4 Estados

Cada vista soportará carga, datos, vacío, error recuperable y advertencia metodológica. Los skeletons conservarán el tamaño final. Los estados vacíos explicarán qué filtro produjo la ausencia. Las unidades permanecerán visibles en indicadores, ejes, tooltips y tablas.

## 11. Rendimiento y seguridad

- Índices compuestos para territorio, periodo, cultivo y versión activa.
- Consultas agregadas específicas para cada visualización.
- Paginación y límites obligatorios en detalle.
- Geometrías simplificadas para la web y geometrías completas fuera de las respuestas ordinarias.
- No se añade Redis en el MVP. Se evaluará solo con evidencia de consultas lentas después de índices y planes SQL.
- Variables sensibles permanecen en entorno; `.env` no se versiona.
- CORS se limita a los orígenes configurados.
- No hay endpoints públicos de importación ni escritura.

## 12. Pruebas y verificación

### Backend y datos

- Pruebas unitarias de agregación, rendimiento ponderado, variaciones y compatibilidad temporal.
- Pruebas del ETL con fixtures mínimos que cubran cada tipo de periodo, cero, duplicado, error y advertencia.
- Prueba de idempotencia por hash.
- Prueba de rollback ante fallo fatal.
- Pruebas de integración contra PostgreSQL/PostGIS.
- Pruebas de API para filtros, paginación, ordenamiento, errores y exportaciones.
- Conciliación del archivo completo: filas, totales por año y agregación equivalente a `BaseSIPRA`.

### Frontend

- Pruebas unitarias de normalización de respuestas, filtros dependientes y formato de unidades.
- Pruebas de componentes para carga, vacío, error y advertencia.
- Pruebas E2E para navegación; Dashboard → Consulta → Exportación; comparación; y selección territorial.
- Verificación responsive en escritorio, tablet y móvil.
- Navegación por teclado, foco visible, etiquetas y contraste WCAG AA.

Lint, pruebas y compilación se ejecutarán al finalizar cada corte vertical.

## 13. Entregas verticales

El plan de implementación que sigue a esta especificación cubrirá exclusivamente el Corte 1. Los cortes posteriores se planificarán cuando el anterior esté verificado, conservando los contratos y límites definidos aquí.

### Corte 1 — Fundamento y Dashboard real

- Estructura del monorepositorio.
- Docker Compose, variables, migraciones y documentación inicial.
- Modelo de procedencia, catálogos y hechos.
- ETL idempotente y conciliación.
- Endpoints de catálogos, resumen, series y rankings.
- Armazón visual aprobado y Dashboard conectado a datos reales.

### Corte 2 — Consulta y distribución

- Registros paginados.
- Filtros dependientes.
- CSV y Excel.
- Repositorio de fuentes y versiones.

### Corte 3 — Análisis territorial e histórico

- Comparador con reglas de compatibilidad.
- Cartografía oficial versionada.
- Geovisor y selección territorial.
- Página Acerca de.

### Corte 4 — Endurecimiento

- Responsive completo.
- Accesibilidad.
- Optimización de consultas y geometrías.
- Cobertura E2E y conciliación final.
- Manual de ejecución para Windows y registro de limitaciones.

Cada corte debe migrar, importar, probar y compilar independientemente. Una función dependiente de una fuente o geometría ausente permanecerá explícitamente incompleta.

## 14. Criterios de aceptación

EVA Explorer 1.0 queda aceptado cuando:

1. `/` abre el Dashboard, sin landing promocional.
2. Las seis rutas funcionan y comparten identidad visual.
3. El ETL importa la versión suministrada sin modificarla y conserva procedencia.
4. La conciliación con `BaseSIPRA` pasa.
5. Dashboard, consultas, comparador y mapa usan datos reales.
6. Filtros dependientes y selección territorial funcionan.
7. Tablas, paginación, ordenamiento y exportaciones funcionan desde backend.
8. Comparaciones incompatibles se bloquean o advierten explícitamente.
9. El rendimiento agregado siempre es ponderado.
10. La cartografía tiene fuente oficial verificable y unión DIVIPOLA.
11. Los componentes consumen datos mediante `services/`.
12. La interfaz es usable por teclado y responsive.
13. OpenAPI, README y ejecución en Windows están documentados.
14. Lint, compilaciones y pruebas implementadas finalizan correctamente.

## 15. Decisiones finales

- Monolito modular, no microservicios.
- PostgreSQL/PostGIS como fuente de consulta.
- `BasePagina` como hecho y `BaseSIPRA` como control.
- Datos reales desde el primer corte.
- Dirección visual “Analítica institucional”.
- MapLibre GL JS como primera opción GIS.
- Parámetros de URL y capa de servicios frontend.
- Sin autenticación, Redis, cola de trabajos ni datos ficticios en el MVP.
