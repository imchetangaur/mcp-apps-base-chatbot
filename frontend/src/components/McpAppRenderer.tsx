import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';
import { RemoteDomRenderer, type RemoteDomNode } from './RemoteDomRenderer';

interface Props {
  /** Raw content from MCP server (HTML string or JSON component tree) */
  content: string;
  /** MIME type: text/html or application/vnd.mcp-ui.remote-dom */
  mimeType?: string;
  title?: string;
  /** Called when user interacts with content (clicks a card, etc.) */
  onAction?: (text: string) => void;
}

const REMOTE_DOM_MIME = 'application/vnd.mcp-ui.remote-dom';

/**
 * MCP App Renderer — routes between rendering modes based on mimeType:
 *
 * 1. text/html → sandboxed iframe (legacy)
 * 2. application/vnd.mcp-ui.remote-dom → native React components (Remote DOM)
 *
 * Remote DOM provides:
 * - Native theming (inherits host dark theme)
 * - Direct click handlers (no postMessage chain)
 * - No iframe overhead
 * - Seamless visual integration
 */
export function McpAppRenderer({ content, mimeType, title, onAction }: Props) {
  const isRemoteDom = mimeType === REMOTE_DOM_MIME;

  if (isRemoteDom) {
    return (
      <RemoteDomContent
        content={content}
        title={title}
        onAction={onAction}
      />
    );
  }

  // Fallback: iframe-based HTML rendering
  return (
    <IframeContent
      html={content}
      title={title}
      onAction={onAction}
    />
  );
}

/** Remote DOM: renders JSON component tree as native React components */
function RemoteDomContent({
  content,
  title,
  onAction,
}: {
  content: string;
  title?: string;
  onAction?: (text: string) => void;
}) {
  const tree = useMemo<RemoteDomNode | null>(() => {
    try {
      return JSON.parse(content);
    } catch {
      return null;
    }
  }, [content]);

  if (!tree) {
    return (
      <div className="mcp-app-renderer">
        <div className="mcp-app-toolbar">
          <span className="mcp-app-title">{title || 'MCP App'}</span>
        </div>
        <div style={{ padding: 16, color: 'var(--error)' }}>
          Failed to parse Remote DOM content
        </div>
      </div>
    );
  }

  return (
    <div className="mcp-app-renderer mcp-remote-dom">
      <RemoteDomRenderer tree={tree} onAction={onAction} />
    </div>
  );
}

/** Iframe: renders raw HTML in a sandboxed iframe via proxy */
function IframeContent({
  html,
  title,
  onAction,
}: {
  html: string;
  title?: string;
  onAction?: (text: string) => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(300);
  const [displayMode, setDisplayMode] = useState<'inline' | 'fullscreen'>('inline');
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      const data = event.data;
      if (!data || typeof data !== 'object') return;

      if (data.type === 'sandbox-ready') {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'load-html', html },
          '*'
        );
        setLoaded(true);
      }

      if (data.type === 'resize' && typeof data.height === 'number') {
        setHeight(Math.min(Math.max(data.height, 100), 800));
      }

      if (data.type === 'mcp-action' && onAction) {
        if (typeof data.text === 'string' && data.text.trim()) {
          onAction(data.text);
        }
      }
    }

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [html, onAction]);

  const toggleFullscreen = useCallback(() => {
    setDisplayMode((prev) => (prev === 'inline' ? 'fullscreen' : 'inline'));
  }, []);

  useEffect(() => {
    if (displayMode !== 'fullscreen') return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setDisplayMode('inline');
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [displayMode]);

  const isFullscreen = displayMode === 'fullscreen';

  return (
    <div className={`mcp-app-renderer ${isFullscreen ? 'mcp-fullscreen' : ''}`}>
      <div className="mcp-app-toolbar">
        <span className="mcp-app-title">{title || 'MCP App'}</span>
        <div className="mcp-app-actions">
          <button
            className="btn-icon"
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>
      <div
        className="mcp-app-iframe-container"
        style={{ height: isFullscreen ? '100%' : `${height}px` }}
      >
        {!loaded && <div className="mcp-app-loading">Loading MCP app...</div>}
        <iframe
          ref={iframeRef}
          src="/api/mcp-proxy/sandbox"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            opacity: loaded ? 1 : 0,
          }}
        />
      </div>
    </div>
  );
}
