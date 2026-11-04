import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AssistantWidget } from './assistant-widget';

afterEach(() => vi.unstubAllGlobals());

it('preserves a new draft when an earlier question fails', async () => {
  let reject!: (reason: Error) => void;
  vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise((_, fail) => { reject = fail; })));
  render(<AssistantWidget />);
  fireEvent.click(screen.getByRole('button', { name: 'Abrir asistente de datos' }));
  fireEvent.change(screen.getByLabelText('Tu pregunta'), { target: { value: 'café' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enviar pregunta' }));
  fireEvent.change(screen.getByLabelText('Tu pregunta'), { target: { value: 'cacao en Huila' } });
  await act(async () => reject(new Error('Sin conexión')));
  expect(screen.getByLabelText('Tu pregunta')).toHaveValue('cacao en Huila');
});

it('opens, sends a question, displays sourced facts and returns focus on Escape', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({
    status: 'answer', answer: 'Huila lidera el ranking.',
    facts: [{ label: 'Huila', value: '1250', unit: 'ha' }],
    source: 'EVA, publicada por UPRA', warnings: [], applied_filters: {},
    dashboard_url: '/?year=2025&crop=1', source_version: '2025',
  }) }));
  render(<AssistantWidget />);
  const launcher = screen.getByRole('button', { name: 'Abrir asistente de datos' });
  fireEvent.click(launcher);
  fireEvent.change(screen.getByLabelText('Tu pregunta'), { target: { value: '¿Dónde se cultiva más café?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enviar pregunta' }));
  expect(await screen.findByText('Huila lidera el ranking.')).toBeVisible();
  expect(screen.getByText('1.250 ha')).toBeVisible();
  expect(screen.getByText(/EVA, publicada por UPRA/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Ver en Resumen General' })).toHaveAttribute('href', '/?year=2025&crop=1');
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

it('shows a recoverable configuration error without fabricated results', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: {
    message: 'Asistente pendiente de configuración.',
  } }) }));
  render(<AssistantWidget />);
  fireEvent.click(screen.getByRole('button', { name: 'Abrir asistente de datos' }));
  fireEvent.change(screen.getByLabelText('Tu pregunta'), { target: { value: 'café' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enviar pregunta' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Asistente pendiente de configuración.');
  expect(screen.queryByRole('link', { name: 'Ver en Resumen General' })).not.toBeInTheDocument();
});
