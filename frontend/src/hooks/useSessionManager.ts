import { useState, useEffect, useCallback } from 'react';
import { Session } from '../types/session';
import * as sessionsApi from '../api/sessions';

export function useSessionManager() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const list = await sessionsApi.listSessions();
      setSessions(list);
    } catch (err) {
      console.error('Failed to list sessions', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createSession = useCallback(async (name?: string) => {
    const session = await sessionsApi.createSession(name);
    setActiveSessionId(session.id);
    await refresh();
    return session;
  }, [refresh]);

  const deleteSession = useCallback(async (id: string) => {
    await sessionsApi.deleteSession(id);
    if (activeSessionId === id) {
      setActiveSessionId(null);
    }
    await refresh();
  }, [activeSessionId, refresh]);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  return {
    sessions,
    activeSessionId,
    loading,
    createSession,
    deleteSession,
    selectSession,
    refresh,
  };
}
