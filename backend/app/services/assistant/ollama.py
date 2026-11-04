"""Local interpretation only. Validated actions are executed by the analytics service."""

import json
from urllib.request import Request, urlopen

from app.schemas.assistant import SelectedAction
from app.services.assistant.provider import INSTRUCTIONS


def select_local_action(settings, request, latest_year, catalog):
    schema = SelectedAction.model_json_schema()
    schema["required"] = list(schema["properties"])
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "think": False,
        "keep_alive": "15m",
        "format": schema,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 400},
        "messages": [
            {
                "role": "system",
                "content": INSTRUCTIONS
                + f"\nÚltimo año: {latest_year}. Devuelve únicamente el objeto JSON."
                + '\nEjemplo para ¿Dónde se cultiva más café?: '
                + '{"action":"rank","dimension":"department",'
                + '"indicator":"harvested_area_ha","crop":"Café",'
                + '"department":null,"municipality":null,"year_from":null,'
                + '"year_to":null,"period_type":null}.'
                + '\nIMPORTANTE: año agrícola y un año como 2025 NO significan ANNUAL. '
                + 'period_type debe ser null salvo petición explícita del período de fuente.',
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": request.question,
                        "history": [m.model_dump() for m in request.history],
                        "active_context": request.context.model_dump(mode="json")
                        if request.context
                        else None,
                        "catalog": catalog,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    http_request = Request(
        settings.ollama_base_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(http_request, timeout=settings.ollama_timeout) as response:
        result = json.load(response)
    return SelectedAction.model_validate_json(result["message"]["content"])
