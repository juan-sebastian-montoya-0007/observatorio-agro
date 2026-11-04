from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.rate_limit import SlidingWindowRateLimiter
from app.db.session import session_factory
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.assistant.provider import select_action
from app.services.assistant.service import AssistantService
from app.services.assistant.ollama import select_local_action

router = APIRouter(prefix="/assistant", tags=["assistant"])
limiter = SlidingWindowRateLimiter()


def fail(status, code, message, headers=None):
    raise HTTPException(status, detail={"code": code, "message": message}, headers=headers)


def answer_question(question, settings):
    from openai import OpenAI

    with session_factory() as session:
        service = AssistantService(session)
        latest = service.version.coverage_end_year if service.version else 2025
        catalog = service.catalog(question.context)
        if settings.assistant_provider == 'ollama':
            try:
                action = select_local_action(settings, question, latest, catalog)
            except Exception:
                fail(503, 'LOCAL_AI_UNAVAILABLE',
                     'La IA local no respondió. Comprueba que Ollama esté iniciado y que el modelo esté descargado; vuelve a intentarlo.')
            return service.execute(action)
        try:
            with OpenAI(
                api_key=settings.openai_api_key.get_secret_value(), timeout=20, max_retries=0
            ) as client:
                action = select_action(client, settings.openai_model, question, latest, catalog)
        except Exception as error:
            if getattr(error, 'code', None) in ('credit_balance_exhausted', 'insufficient_quota'):
                fail(503, 'AI_CREDIT_REQUIRED',
                     'El proyecto de OpenAI no tiene saldo disponible. '
                     'Su administrador debe añadir saldo para activar las respuestas.')
            fail(
                502,
                "AI_PROVIDER_UNAVAILABLE",
                "La IA no está disponible. Revisa la conexión, la clave "
                "y el saldo de la API, e inténtalo de nuevo.",
            )
        return service.execute(action)


@router.post("/query", response_model=AssistantResponse)
async def query(request: Request):
    delay = limiter.check(request.client.host if request.client else "local")
    if delay:
        fail(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Has alcanzado el límite. Espera un minuto.",
            {"Retry-After": str(delay)},
        )
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 24000:
            fail(413, "REQUEST_TOO_LARGE", "La conversación supera el tamaño permitido.")
    try:
        question = AssistantRequest.model_validate_json(bytes(body))
    except ValidationError:
        fail(
            422,
            "INVALID_QUESTION",
            "Escribe hasta 500 caracteres y como máximo seis mensajes de contexto.",
        )
    settings = request.app.state.settings
    if settings.assistant_provider == 'openai' and not settings.openai_api_key:
        fail(503, "ASSISTANT_NOT_CONFIGURED", "Asistente pendiente de configuración.")
    try:
        return await run_in_threadpool(answer_question, question, settings)
    except SQLAlchemyError:
        fail(503, 'DATA_UNAVAILABLE',
             'La base de datos no está disponible. Inicia los servicios locales e inténtalo de nuevo.')
