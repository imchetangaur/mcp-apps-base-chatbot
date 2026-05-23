import { useState, useCallback, useEffect } from 'react';
import { useSessionManager } from './hooks/useSessionManager';
import { SessionSidebar } from './components/SessionSidebar';
import { ChatView } from './components/ChatView';
import type { McpUiTheme } from './components/McpAppRenderer';

export default function App() {
  const {
    sessions,
    activeSessionId,
    createSession,
    deleteSession,
    selectSession,
    refresh,
  } = useSessionManager();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<McpUiTheme>(() => {
    const saved = localStorage.getItem('theme');
    return (saved === 'light' || saved === 'dark') ? saved : 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    document.documentElement.classList.add('theme-switching');
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.documentElement.classList.remove('theme-switching');
      });
    });
  }, []);

  const handleSelectSession = useCallback(
    (id: string) => {
      selectSession(id);
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    },
    [selectSession]
  );

  const handleCreate = useCallback(() => {
    createSession();
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }, [createSession]);

  return (
    <div className={`app-layout ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={handleSelectSession}
        onCreate={handleCreate}
        onDelete={deleteSession}
        onCollapse={() => setSidebarOpen(false)}
      />
      <main className="main-content">
        {activeSessionId ? (
          <ChatView
            sessionId={activeSessionId}
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            sidebarOpen={sidebarOpen}
            onSessionRenamed={refresh}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
        ) : (
          <div className="welcome-screen">
            <h1>MCP Apps Base Chatbot</h1>
            <p>Create a new chat or select an existing one to get started.</p>
            <button className="btn-primary" onClick={handleCreate}>
              New Chat
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
