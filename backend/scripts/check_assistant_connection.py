"""Verify the running local assistant without reading or sending API credentials."""
import json
from urllib.request import Request, urlopen

request = Request(
    'http://localhost:8000/api/v1/assistant/query',
    data=json.dumps({'question': '¿Dónde se cultiva más café?'}).encode(),
    headers={'Content-Type': 'application/json'}, method='POST',
)
try:
    with urlopen(request, timeout=190) as response:
        result = json.load(response)
    print('Estado:', result['status'])
    print(result['answer'])
    print(result['source'])
except Exception as error:
    print('Asistente no disponible:', type(error).__name__)
    raise SystemExit(1)
