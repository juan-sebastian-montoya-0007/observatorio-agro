'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { MessageCircle, Send, Sprout, Trash2, X, LoaderCircle, ArrowUpRight } from 'lucide-react';
import { askAssistant, type AssistantResult, type ChatMessage } from '@/services/assistant';
import './assistant.css';

type Entry = ChatMessage & { result?: AssistantResult };
const examples = ['¿Dónde se cultiva más café?', '¿Qué departamento produjo más maíz en 2024?', '¿Cómo evolucionó la producción de cacao entre 2019 y 2025?'];

export function AssistantWidget() {
  const reducedMotion = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const launcher = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);

  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages, busy, open]);
  useEffect(() => () => controller.current?.abort(), []);

  function close() { setOpen(false); launcher.current?.focus(); }
  function clear() {
    requestId.current += 1;
    controller.current?.abort();
    controller.current = null;
    setBusy(false); setMessages([]); setError(''); setQuestion('');
    input.current?.focus();
  }
  async function submit(text = question) {
    const trimmed = text.trim();
    if (!trimmed || trimmed.length > 500 || controller.current) return;
    const id = ++requestId.current;
    const next: Entry[] = [...messages, { role: 'user', content: trimmed }];
    const abort = new AbortController();
    controller.current = abort;
    const timeout = window.setTimeout(() => abort.abort(), 190000);
    setMessages(next.slice(-20)); setQuestion(''); setError(''); setBusy(true);
    try {
      const result = await askAssistant(trimmed, messages.slice(-6).map(({ role, content }) => ({ role, content: content.slice(0, 3000) })), abort.signal);
      if (id !== requestId.current) return;
      setMessages([...next, { role: 'assistant', content: result.answer, result }].slice(-20) as Entry[]);
    } catch (caught) {
      if (id !== requestId.current) return;
      setMessages(messages);
      setQuestion(current => current || trimmed);
      setError(caught instanceof Error && caught.name !== 'AbortError' ? caught.message : 'La consulta tardó demasiado. Puedes intentarlo de nuevo.');
    } finally {
      window.clearTimeout(timeout);
      if (id === requestId.current) { controller.current = null; setBusy(false); }
    }
  }

  return <div className="agro-assistant">
    {open && <motion.section initial={{ opacity: 0, y: reducedMotion ? 0 : 18, scale: reducedMotion ? 1 : 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} style={{ transformOrigin: "bottom right" }} id="agro-assistant-panel" role="dialog" aria-label="Asistente de datos de Observatorio Agro" className="agro-chat" onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); close(); } }}>
      <header className="agro-chat-header"><span className="agro-chat-brand"><Sprout size={24} /><span><strong>Asistente Agro</strong><small>IA local · sin créditos</small></span></span><div><button type="button" onClick={clear} aria-label="Limpiar conversación" title="Limpiar conversación"><Trash2 size={17} /></button><button type="button" onClick={close} aria-label="Cerrar asistente"><X size={21} /></button></div></header>
      <div className="agro-chat-log" ref={log} role="log" aria-label="Conversación" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 && <div className="agro-chat-welcome"><span className="agro-chat-leaf"><Sprout size={32} /></span><h2>¿Qué quieres conocer del campo?</h2><p>Consulta áreas, producción y rendimiento. Respondo únicamente con los datos disponibles del Observatorio.</p><div className="agro-chat-examples">{examples.map(example => <button type="button" key={example} onClick={() => void submit(example)}>{example}<ArrowUpRight size={16} /></button>)}</div></div>}
        {messages.map((message, index) => <article key={index} className={`agro-chat-message agro-chat-message--${message.role}`}><small>{message.role === 'user' ? 'Tú' : 'Asistente Agro'}</small><p>{message.content}</p>{message.result && <>
          {message.result.facts.length > 0 && <dl>{message.result.facts.map((fact, i) => <div key={i}><dt>{fact.label}</dt><dd>{fact.value === null ? 'Sin datos' : `${new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(Number(fact.value))} ${fact.unit}`}</dd></div>)}</dl>}
          <p className="agro-chat-source">{message.result.source}{message.result.source_version && ` Versión ${message.result.source_version}.`}</p>
          {message.result.warnings.map((warning, i) => <p className="agro-chat-warning" key={i}>{warning}</p>)}
          {message.result.dashboard_url?.startsWith('/?') && <a href={message.result.dashboard_url}>Ver en Resumen General <ArrowUpRight size={14} /></a>}
        </>}</article>)}
        {busy && <p role="status" className="agro-chat-loading"><LoaderCircle size={16} /> Consultando con IA local…</p>}
      </div>
      <form className="agro-chat-compose" onSubmit={event => { event.preventDefault(); void submit(); }}>
        {error && <p role="alert" className="agro-chat-error">{error}</p>}
        <label htmlFor="agro-chat-question">Tu pregunta</label><div><textarea id="agro-chat-question" ref={input} rows={2} maxLength={500} value={question} onChange={event => setQuestion(event.target.value)} placeholder="Pregunta por un cultivo, territorio o año…" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); } }} /><button type="submit" disabled={busy || !question.trim()} aria-label="Enviar pregunta"><Send size={19} /></button></div>
        <small>Datos EVA · UPRA · {question.length}/500. No compartas datos personales. Procesamiento local con Ollama.</small>
      </form>
    </motion.section>}
    <motion.button whileHover={reducedMotion ? undefined : { scale: 1.04 }} whileTap={reducedMotion ? undefined : { scale: 0.96 }} type="button" ref={launcher} className="agro-chat-launcher" aria-label={open ? 'Cerrar asistente de datos' : 'Abrir asistente de datos'} aria-expanded={open} aria-controls="agro-assistant-panel" onClick={() => open ? close() : setOpen(true)}>{open ? <X size={25} /> : <MessageCircle size={27} />}<span>Asistente IA</span></motion.button>
  </div>;
}
