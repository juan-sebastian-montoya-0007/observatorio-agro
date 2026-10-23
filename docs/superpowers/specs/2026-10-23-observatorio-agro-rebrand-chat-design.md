# Observatorio Agro — rediseño de marca y asistente de datos

**Fecha:** 2026-10-23  
**Estado:** pendiente de aprobación  
**Producto actual:** EVA Explorer  
**Nombre aprobado:** Observatorio Agro

## Intención

Convertir la plataforma en **Observatorio Agro**, un observatorio público de consulta agropecuaria. EVA deja de ser la identidad del producto y aparece únicamente como procedencia verificable de los datos. El mapa territorial se integra en el Resumen General y deja de existir como módulo independiente. La experiencia incorpora un asistente conversacional capaz de responder preguntas sobre la base cargada sin inventar cifras.

## Objetivos

- Usar **Observatorio Agro** como única marca visible del producto.
- Eliminar la entrada independiente **Geovisor** de la navegación.
- Mantener la visualización cartográfica dentro de **Resumen General**.
- Dar a todos los gráficos cartesianos nombres de ejes, indicador y unidad visibles y accesibles.
- Permitir preguntas en lenguaje natural como “¿Dónde se cultiva más café?”.
- Responder únicamente con resultados obtenidos mediante consultas controladas a la base agropecuaria.
- Mostrar en cada respuesta relevante el periodo, territorio, unidad, filtros aplicados y la atribución de la fuente.

## No objetivos

- El asistente no responderá preguntas agrícolas generales ni dará recomendaciones técnicas, financieras o productivas.
- El modelo de IA no calculará ni inventará indicadores; los cálculos seguirán en el backend analítico.
- No se cambiarán nombres técnicos internos que describen correctamente el formato o importador EVA.
- No se publicará ni desplegará externamente en este corte; el trabajo seguirá siendo local.
- No se creará una página independiente de Geovisor.

## Restricciones y principios

- El archivo fuente y los datos importados no se modificarán.
- La clave del proveedor de IA residirá solo en el backend mediante variable de entorno; nunca se enviará al navegador ni se guardará en Git.
- El backend solo expondrá al modelo herramientas de lectura con parámetros validados y límites explícitos.
- El asistente será público y no requerirá registro ni inicio de sesión. El backend aplicará límites de frecuencia, tamaño y consumo para controlar abuso y costos.
- Las respuestas distinguirán entre ausencia de datos, filtros incompatibles y errores de servicio.
- La atribución pública será equivalente a: “Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA”.
- El asistente indicará cuando no pueda responder con la base disponible y no completará la respuesta con conocimiento externo.

## Enfoques considerados

### 1. IA con consultas controladas — seleccionado

Un modelo interpreta la pregunta y selecciona una herramienta de lectura; el backend valida los argumentos, ejecuta consultas determinísticas y entrega los resultados. El modelo redacta la respuesta únicamente a partir de esos resultados.

**Ventajas:** comprende variaciones del lenguaje, conserva una conversación natural y mantiene las cifras bajo control del backend.  
**Costo:** requiere una clave de API y manejo explícito de fallos o límites del proveedor.

### 2. Chat determinístico sin IA externa

Un analizador local reconoce un conjunto cerrado de frases e intenciones.

**Ventajas:** funciona sin proveedor externo.  
**Desventajas:** entiende pocas formulaciones, escala mal y ofrece una experiencia menos natural.

### 3. Chat general con acceso directo a la base

El modelo responde libremente y genera consultas abiertas.

**Descartado:** debilita la trazabilidad, aumenta el riesgo de consultas inseguras y permite respuestas fuera de los datos aprobados.

## Marca y contenido público

- Sustituir “EVA Explorer” por “Observatorio Agro” en encabezado, navegación, metadatos del navegador, textos introductorios y documentación pública.
- Conservar “EVA” solo en secciones de fuente, metodología, procedencia y detalles de importación.
- La marca lateral mostrará “Observatorio Agro” y una descripción breve orientada a consulta pública.
- El Resumen General seguirá siendo la portada.
- El menú no incluirá Geovisor. Las rutas antiguas de Geovisor, si llegan a existir, redirigirán al Resumen General y no mostrarán una experiencia duplicada.

## Navegación resultante

1. Resumen General
2. Consultas
3. Comparador
4. Repositorio
5. Acerca de

El mapa territorial será una sección del Resumen General con los mismos filtros globales que los indicadores y gráficos.

## Ejes y semántica de gráficos

- Todo gráfico cartesiano tendrá nombre visible en el eje X y en el eje Y.
- El eje X indicará la dimensión: año, territorio, cultivo u otra categoría.
- El eje Y indicará el indicador y su unidad, por ejemplo “Producción (t)” o “Rendimiento (t/ha)”.
- Los nombres de ejes también estarán disponibles para tecnologías de asistencia.
- Tooltips, leyendas y formatos numéricos usarán las mismas etiquetas y unidades del eje.
- Gráficos no cartesianos, como dona o mapa, tendrán título, leyenda, unidad y descripción accesible en vez de ejes artificiales.

## Experiencia del asistente

### Ubicación

Un botón flotante “Asistente de datos” estará disponible en todas las páginas. Al abrirlo mostrará un panel lateral en escritorio y una vista superpuesta de ancho completo en móvil. No ocultará permanentemente los filtros ni el contenido principal.

### Inicio

El panel explicará su alcance y ofrecerá ejemplos breves:

- “¿Dónde se cultiva más café?”
- “¿Qué departamento produjo más maíz en 2024?”
- “¿Cómo evolucionó el área cosechada de cacao entre 2019 y 2025?”

### Respuesta

Cada respuesta de datos incluirá:

- una conclusión breve en lenguaje natural;
- la cifra principal y su unidad;
- periodo y lectura temporal;
- territorio o dimensión consultada;
- filtros aplicados;
- fuente de datos;
- un enlace o acción para abrir el Resumen General con esos filtros, cuando corresponda.

Ejemplo de estructura, sin cifras predefinidas:

> El departamento con mayor área cosechada de café en 2025 es **[departamento]**, con **[valor] ha**. Se compararon los departamentos disponibles para el año agrícola 2025. Fuente: Evaluaciones Agropecuarias Municipales (EVA), UPRA.

### Conversación

- La primera versión conservará el contexto reciente dentro de la sesión del navegador para entender continuaciones como “¿y en 2024?”.
- El usuario podrá limpiar la conversación.
- No se almacenará un historial personal en la base de datos.
- Al recargar la página puede comenzar una sesión nueva; la persistencia entre dispositivos queda fuera del alcance.

## Arquitectura del asistente

### Frontend

- Componente global del asistente en el shell de la aplicación.
- Estado de conversación limitado y controlado en el cliente.
- Envío de pregunta, contexto reciente y filtros activos al backend.
- Estados explícitos: listo, consultando, respuesta, sin datos, fuera de alcance y error recuperable.
- Texto de descargo breve: “Responde únicamente con los datos disponibles en el Observatorio Agro”.

### Backend

- Endpoint público de solo lectura, sin cuenta de usuario, protegido mediante límites de frecuencia, tamaño de solicitud, tiempo máximo y presupuesto de herramientas.
- Validación de longitud, estructura y frecuencia básica de las solicitudes.
- Orquestación mediante herramientas de solo lectura; el modelo nunca recibirá credenciales de base de datos ni SQL libre.
- Modelo y proveedor configurables mediante variables de entorno.
- Tiempo máximo y mensajes de error estables cuando el proveedor no esté disponible.

### Herramientas permitidas

La primera versión utilizará contratos tipados equivalentes a:

- `rank_territories`: clasificar departamentos o municipios por indicador, cultivo y periodo.
- `summarize_selection`: resumir áreas, producción y rendimiento para filtros válidos.
- `get_time_series`: consultar evolución temporal para una selección.
- `rank_crops`: clasificar cultivos dentro de un territorio y periodo.

Cada herramienta reutilizará servicios/repositorios analíticos existentes. No aceptará SQL ni nombres arbitrarios sin resolverlos primero contra catálogos válidos.

### Flujo de una pregunta

1. El frontend envía pregunta, filtros activos y contexto reciente acotado.
2. El backend entrega al modelo únicamente instrucciones de alcance y esquemas de herramientas.
3. El modelo solicita una herramienta con argumentos estructurados.
4. El backend valida cultivos, territorios, periodo, indicador y límites.
5. El backend ejecuta la consulta determinística.
6. El modelo redacta usando solamente el resultado estructurado.
7. El backend devuelve respuesta, hechos citables, filtros y fuente para que el frontend los muestre por separado.

## Respuestas seguras y verificables

- Si una pregunta está fuera del dominio, responderá que el asistente solo consulta datos del Observatorio Agro.
- Si falta un periodo o indicador indispensable, podrá hacer una pregunta aclaratoria breve o aplicar el filtro activo visible y declararlo.
- Si hay varias coincidencias de cultivo o territorio, pedirá precisión en lugar de escoger silenciosamente.
- Si no hay registros, dirá “No encontré datos para esos filtros”.
- Si el modelo genera texto que contradice los hechos estructurados, el backend conservará los hechos como fuente de verdad y la respuesta se rechazará o reconstruirá con una plantilla segura.
- Los resultados numéricos conservarán la política estadística del sistema: el rendimiento agregado es producción total dividida por área cosechada total.

## Configuración local

- `OPENAI_API_KEY`: secreto disponible únicamente para el backend.
- `OPENAI_MODEL`: modelo configurable y con valor documentado, no fijado en el frontend.
- Sin clave, el resto del Observatorio Agro seguirá funcionando y el panel explicará que el asistente no está configurado.
- `.env.example` documentará las variables sin contener secretos reales.

## Pruebas y aceptación

### Marca y navegación

- No aparece “EVA Explorer” en la interfaz ni en metadatos públicos.
- “Observatorio Agro” aparece como marca principal.
- Geovisor no aparece en el menú.
- EVA aparece únicamente en atribución, metodología o procedencia de datos.

### Gráficos

- Serie histórica y barras muestran nombres de ambos ejes con unidades correctas.
- Tooltips y ejes coinciden en indicador y unidad.
- Dona y mapa tienen alternativa descriptiva accesible.

### Asistente

- Una pregunta sobre mayor cultivo/producción genera una llamada a herramienta y devuelve resultados de la base, no cifras inventadas.
- Una continuación temporal utiliza el contexto reciente.
- Preguntas generales o fuera de alcance se rechazan de forma útil.
- Ambigüedad, ausencia de datos, caída del proveedor y falta de clave tienen estados probados.
- La clave nunca aparece en respuestas, bundle del frontend, logs de prueba ni repositorio.
- Un visitante puede utilizar el asistente sin iniciar sesión y recibe un error estable y comprensible si excede los límites de uso.
- La acción “Ver en Resumen General” genera filtros compatibles con la URL existente.

### Verificación final

- Pruebas unitarias de contratos, herramientas, validación y componentes.
- Pruebas de integración del endpoint con el proveedor simulado y repositorio real de pruebas.
- Prueba de navegador del flujo: abrir asistente, preguntar por café, inspeccionar respuesta y abrir el dashboard filtrado.
- Revisión responsive y accesible en escritorio y móvil.

## Decisiones dejadas al constructor

- Nombre exacto de archivos y separación interna siguiendo los patrones del repositorio.
- Modelo concreto configurado por defecto, siempre que sea compatible con herramientas estructuradas y quede documentado.
- Límites precisos de longitud, contexto y frecuencia, con valores conservadores y pruebas.
- Detalles visuales menores del panel manteniendo el lenguaje verde, sobrio y analítico de la propuesta aprobada.

