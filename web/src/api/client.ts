import type { DebateSession, Message } from '../types/debate';

const BASE = '/api';

export async function createDebate(
  topic: string,
  mode: string = 'standard',
): Promise<{ id: string; topic: string; status: string }> {
  const r = await fetch(`${BASE}/debates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, mode, tts_enabled: false }),
  });
  if (!r.ok) throw new Error(`Create failed: ${r.status}`);
  return r.json();
}

export async function listDebates(
  search: string = '',
  sort: string = 'newest',
  limit: number = 50,
): Promise<DebateSession[]> {
  const params = new URLSearchParams({ limit: String(limit), search, sort });
  const r = await fetch(`${BASE}/debates?${params}`);
  if (!r.ok) throw new Error(`List failed: ${r.status}`);
  const data = await r.json();
  return data.debates ?? data;
}

export async function deleteDebate(id: string): Promise<void> {
  const r = await fetch(`${BASE}/debates/${id}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(`Delete failed: ${r.status}`);
}

export async function getDebate(id: string): Promise<{
  session: DebateSession;
  messages: Message[];
  rounds: unknown[];
}> {
  const r = await fetch(`${BASE}/debates/${id}`);
  if (!r.ok) throw new Error(`Get failed: ${r.status}`);
  return r.json();
}

export async function pauseDebate(id: string): Promise<void> {
  await fetch(`${BASE}/debates/${id}/pause`, { method: 'POST' });
}

export async function resumeDebate(id: string): Promise<void> {
  await fetch(`${BASE}/debates/${id}/resume`, { method: 'POST' });
}

export async function stopDebate(id: string): Promise<void> {
  await fetch(`${BASE}/debates/${id}/stop`, { method: 'POST' });
}

export async function skipRound(id: string): Promise<void> {
  await fetch(`${BASE}/debates/${id}/skip`, { method: 'POST' });
}

export function exportUrl(id: string, format: string = 'markdown'): string {
  return `${BASE}/debates/${id}/export?format=${format}`;
}
