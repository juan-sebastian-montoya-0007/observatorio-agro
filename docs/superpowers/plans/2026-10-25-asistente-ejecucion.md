# Implementación del asistente flotante

Continúa el diseño y plan del 23 de octubre, autorizado por el usuario con IA y clave local ya configurada.

## Decisiones de ejecución

- Mantener todos los cambios actuales; sin commits ni publicación automática.
- Reutilizar AnalyticsService y sus políticas. Una acción tipada por pregunta, sin SQL generado ni cifras redactadas por IA.
- Agrupar contratos, proveedor, resolución y presentación en archivos pequeños. Probar límites, resolución, respuestas y widget.
- API pública local: 10 solicitudes por IP por minuto, límite global, cuerpo acotado, 20 segundos al proveedor y sin reintentos automáticos.
- Botón global abajo a la derecha, panel adaptable, historial acotado en memoria, cerrar con Escape y devolver foco.
- Clave sólo en backend; Docker la recibe de .env. No imprimir secretos ni configuración completa.
- Las pruebas existentes desactualizadas se reportan sin reescribirlas para ocultar fallos.

## Pasos

1. Contratos y pruebas de seguridad, proveedor y consultas.
2. Endpoint y configuración protegida.
3. Widget, servicio y pruebas de interacción.
4. Compilación, prueba local real, revisión y entrega.

## Verificación del 25 de octubre

- Implementados contratos, proveedor Responses con SDK oficial, consultas de sólo lectura, rate limit, API y panel global.
- Revisión independiente detectó año parcial, contexto municipal y pérdida de borrador; corregidos.
- 12 pruebas backend independientes de PostgreSQL y 3 pruebas de interacción frontend pasan.
- Compilación Next.js y TypeScript completada; ESLint del componente y cliente sin errores.
- La llamada real a OpenAI respondió 429 con `credit_balance_exhausted`; requiere saldo del proyecto, no cambiar la clave.
- PostgreSQL local no respondió en 5432. Las pruebas de integración no se pudieron completar.
- Suite frontend: 53 pasan, 4 fallan en chart-guidance, dashboard (2) y app-shell; expectativas de la interfaz anterior y mocks sin datos nuevos. No se alteraron esas pruebas.
- Suite backend detenida tras 3 errores de conexión: aceptación del libro y dos pruebas de agriculture. Se cancelaron procesos que esperaban al motor.
- Interfaz y backend nativos iniciados en 3000 y 8000. No se publicó ni se hizo commit.

## Recuperación de Docker
- Causa observada: sockets Windows inaccesibles dockerInference y engine.sock impedían iniciar Docker Desktop.
- Se conservaron como respaldo las carpetas temporales run y docker-secrets-engine y Docker las regeneró. No se borraron volúmenes ni discos.
- Motor Docker volvió a responder (29.6.1); imágenes reconstruidas con compose.
- Se cerró el servidor Next local del proyecto que ocupaba 3000 y se inició el frontend de Docker.
- API summary con year_from=2025 y year_to=2025: cobertura AVAILABLE, 25.612 registros; página principal HTTP 200.
- La falta de saldo de la API de OpenAI sigue siendo una limitación externa para el chatbot. Framer Motion continúa pendiente.
