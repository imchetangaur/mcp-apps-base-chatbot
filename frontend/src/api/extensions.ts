import { apiGet, apiPost, apiDelete } from './client';
import { ExtensionConfig, ToolInfo } from '../types/extension';

export async function addExtension(sessionId: string, config: ExtensionConfig): Promise<void> {
  await apiPost(`/sessions/${sessionId}/extensions`, config);
}

export async function removeExtension(sessionId: string, name: string): Promise<void> {
  await apiDelete(`/sessions/${sessionId}/extensions/${name}`);
}

export async function listExtensions(sessionId: string): Promise<ExtensionConfig[]> {
  return apiGet<ExtensionConfig[]>(`/sessions/${sessionId}/extensions`);
}

export async function listTools(sessionId: string): Promise<ToolInfo[]> {
  return apiGet<ToolInfo[]>(`/sessions/${sessionId}/tools`);
}
