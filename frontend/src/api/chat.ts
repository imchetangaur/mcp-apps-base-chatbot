import { SSEEvent } from '../types/events';
import { MessageContent } from '../types/message';

/**
 * Send a message and consume the SSE stream.
 * Calls onEvent for each parsed SSE event.
 */
export async function sendMessage(
  sessionId: string,
  content: MessageContent[],
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`/api/sessions/${sessionId}/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    signal,
  });

  if (!res.ok) {
    throw new Error(`Reply failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE lines: each event ends with \n\n
    const parts = buffer.split('\n\n');
    buffer = parts.pop()!; // last part is incomplete

    for (const part of parts) {
      for (const line of part.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as SSEEvent;
            onEvent(event);
          } catch {
            // skip malformed events
          }
        }
      }
    }
  }
}
