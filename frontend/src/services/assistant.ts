export type ChatMessage = { role: 'user' | 'assistant'; content: string };
export type AssistantResult = {
  status: 'answer' | 'no_data' | 'needs_clarification' | 'out_of_scope';
  answer: string;
  facts: { label: string; value: string | null; unit: string }[];
  source: string;
  source_version: string | null;
  warnings: string[];
  dashboard_url: string | null;
  applied_filters: Record<string, unknown>;
};

export async function askAssistant(question: string, history: ChatMessage[], signal: AbortSignal): Promise<AssistantResult> {
  // Only the summary URL represents applied filters. Other modules keep their own draft state.
  const params = new URLSearchParams(window.location.search);
  let context: Record<string, string | number> | undefined;
  if (window.location.pathname === '/' && params.size) {
    context = { year_from: Number(params.get('year') ?? 2025), year_to: Number(params.get('year') ?? 2025) };
    for (const key of ['department', 'municipality', 'period_mode', 'period_type', 'indicator', 'group', 'subgroup', 'cycle', 'classification', 'physical_state']) {
      const value = params.get(key);
      if (value) context[key] = value;
    }
    for (const key of ['crop', 'crop_variant']) {
      const value = params.get(key);
      if (value) context[key] = Number(value);
    }
  }
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');
  const response = await fetch(`${base}/api/v1/assistant/query`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
    body: JSON.stringify({ question, history: history.slice(-6), context }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail?.message === 'string' ? body.detail.message : 'No pudimos consultar el asistente. Inténtalo de nuevo.');
  if (typeof body.answer !== 'string' || !Array.isArray(body.facts) || !Array.isArray(body.warnings) || typeof body.source !== 'string') {
    throw new Error('El asistente devolvió una respuesta no válida. Inténtalo de nuevo.');
  }
  return body;
}
