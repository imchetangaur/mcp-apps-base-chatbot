import { useState, useCallback, useRef } from 'react';
import { Message, TextContent } from '../types/message';
import { SSEEvent } from '../types/events';
import { sendMessage } from '../api/chat';
import { getSession } from '../api/sessions';

export type ChatState = 'idle' | 'loading' | 'streaming' | 'error';

export function useChatStream(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatState, setChatState] = useState<ChatState>('idle');
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load existing session messages
  const loadSession = useCallback(async () => {
    if (!sessionId) return;
    setChatState('loading');
    try {
      const session = await getSession(sessionId);
      setMessages(session.messages);
      setChatState('idle');
    } catch (err) {
      setError('Failed to load session');
      setChatState('error');
    }
  }, [sessionId]);

  // Push or merge a message into the list
  const pushMessage = useCallback((incoming: Message) => {
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === incoming.id);
      if (idx >= 0) {
        // Merge: replace existing message (streaming update)
        const updated = [...prev];
        updated[idx] = incoming;
        return updated;
      }
      return [...prev, incoming];
    });
  }, []);

  // Process an SSE event
  const processEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case 'Message':
          pushMessage(event.message);
          setChatState('streaming');
          break;
        case 'Error':
          setError(event.error);
          setChatState('error');
          break;
        case 'Finish':
          setChatState('idle');
          break;
        case 'Ping':
          // heartbeat, ignore
          break;
      }
    },
    [pushMessage]
  );

  // Submit a user message
  const submit = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: [{ type: 'text', text } as TextContent],
        created: Date.now() / 1000,
      };

      // Optimistically add user message
      setMessages((prev) => [...prev, userMessage]);
      setError(null);
      setChatState('streaming');

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await sendMessage(sessionId, userMessage.content, processEvent, controller.signal);
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Stream failed');
          setChatState('error');
        }
      } finally {
        abortRef.current = null;
        if (chatState === 'streaming') {
          setChatState('idle');
        }
      }
    },
    [sessionId, processEvent, chatState]
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setChatState('idle');
  }, []);

  return {
    messages,
    chatState,
    error,
    submit,
    cancel,
    loadSession,
    setMessages,
  };
}
