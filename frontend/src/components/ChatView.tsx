import { useEffect, useState, useCallback, useRef } from 'react';
import { useChatStream } from '../hooks/useChatStream';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ExtensionManager } from './ExtensionManager';
import { ExtensionConfig } from '../types/extension';
import * as extensionsApi from '../api/extensions';
import { renameSession } from '../api/sessions';
import { Settings, PanelLeftOpen } from 'lucide-react';

interface Props {
  sessionId: string;
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  onSessionRenamed?: () => void;
}

export function ChatView({ sessionId, onToggleSidebar, sidebarOpen, onSessionRenamed }: Props) {
  const { messages, chatState, error, submit, cancel, loadSession } = useChatStream(sessionId);
  const [extensions, setExtensions] = useState<ExtensionConfig[]>([]);
  const [showExtensions, setShowExtensions] = useState(false);
  const hasRenamedRef = useRef(false);

  useEffect(() => {
    loadSession();
    loadExtensions();
    hasRenamedRef.current = false;
  }, [loadSession, sessionId]);

  const loadExtensions = useCallback(async () => {
    try {
      const exts = await extensionsApi.listExtensions(sessionId);
      setExtensions(exts);
    } catch {
      // Extensions may not be loaded yet
    }
  }, [sessionId]);

  const handleAddExtension = useCallback(async (config: ExtensionConfig) => {
    try {
      await extensionsApi.addExtension(sessionId, config);
      await loadExtensions();
    } catch (err: any) {
      alert(`Failed to add extension: ${err.message}`);
    }
  }, [sessionId, loadExtensions]);

  const handleRemoveExtension = useCallback(async (name: string) => {
    try {
      await extensionsApi.removeExtension(sessionId, name);
      await loadExtensions();
    } catch (err: any) {
      alert(`Failed to remove extension: ${err.message}`);
    }
  }, [sessionId, loadExtensions]);

  const handleMcpAction = useCallback((text: string) => {
    if (chatState !== 'streaming' && chatState !== 'loading') {
      submit(text);
    }
  }, [submit, chatState]);

  const handleSubmit = useCallback(async (text: string) => {
    submit(text);

    // Auto-rename session based on first user message
    if (!hasRenamedRef.current) {
      hasRenamedRef.current = true;
      const title = text.length > 40 ? text.slice(0, 40) + '...' : text;
      try {
        await renameSession(sessionId, title);
        onSessionRenamed?.();
      } catch {
        // non-critical
      }
    }
  }, [submit, sessionId, onSessionRenamed]);

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div className="chat-header-left">
          {!sidebarOpen && (
            <button
              className="btn-icon"
              onClick={onToggleSidebar}
              title="Open sidebar"
            >
              <PanelLeftOpen size={18} />
            </button>
          )}
        </div>
        <button
          className="btn-icon"
          onClick={() => setShowExtensions(!showExtensions)}
          title="MCP Servers"
        >
          <Settings size={18} />
          {extensions.length > 0 && (
            <span className="extension-badge">{extensions.length}</span>
          )}
        </button>
      </div>
      <div className="chat-body">
        <div className="chat-messages-area">
          <MessageList
            messages={messages}
            onAction={handleMcpAction}
            isThinking={chatState === 'streaming' || chatState === 'loading'}
          />
          {error && <div className="chat-error">{error}</div>}
        </div>
        {showExtensions && (
          <div className="extensions-panel">
            <ExtensionManager
              sessionId={sessionId}
              extensions={extensions}
              onAdd={handleAddExtension}
              onRemove={handleRemoveExtension}
            />
          </div>
        )}
      </div>
      <ChatInput
        onSubmit={handleSubmit}
        onCancel={cancel}
        disabled={chatState === 'loading'}
        isStreaming={chatState === 'streaming'}
      />
    </div>
  );
}
