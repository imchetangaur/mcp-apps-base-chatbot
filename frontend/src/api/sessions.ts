import { apiGet, apiPost, apiDelete, apiPut } from './client';
import { Session } from '../types/session';
import { Message } from '../types/message';

interface FullSession {
  id: string;
  name: string;
  created: number;
  updated: number;
  messages: Message[];
}

export async function createSession(name?: string): Promise<FullSession> {
  return apiPost<FullSession>('/sessions', { name: name || 'New Chat' });
}

export async function listSessions(): Promise<Session[]> {
  return apiGet<Session[]>('/sessions');
}

export async function getSession(id: string): Promise<FullSession> {
  return apiGet<FullSession>(`/sessions/${id}`);
}

export async function deleteSession(id: string): Promise<void> {
  await apiDelete(`/sessions/${id}`);
}

export async function renameSession(id: string, name: string): Promise<void> {
  await apiPut(`/sessions/${id}/name`, { name });
}
