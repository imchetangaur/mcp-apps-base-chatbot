import { useMemo } from 'react';
import { AppRenderer } from '@mcp-ui/client';
import type { McpUiHostContext } from '@modelcontextprotocol/ext-apps/app-bridge';
import { RemoteDomRenderer, type RemoteDomNode } from './RemoteDomRenderer';

export type McpUiTheme = 'light' | 'dark';

interface Props {
  resource: {
    uri: string;
    mimeType?: string;
    text?: string;
    blob?: string;
  };
  title?: string;
  theme?: McpUiTheme;
  onAction?: (text: string) => void;
}

const REMOTE_DOM_MIME = 'application/vnd.mcp-ui.remote-dom';

const sandboxUrl = new URL('/api/mcp-proxy/mcp-apps-sandbox', window.location.origin);

const DARK_STYLES = {
  '--color-background-primary': '#151515',
  '--color-background-secondary': '#1f1f1f',
  '--color-background-tertiary': '#292929',
  '--color-text-primary': '#ffffff',
  '--color-text-secondary': '#c7c7c7',
  '--color-text-tertiary': '#707070',
  '--color-border-primary': '#383838',
  '--color-border-secondary': '#2a2a2a',
  '--bg-primary': '#151515',
  '--bg-secondary': '#1f1f1f',
  '--bg-surface': '#292929',
  '--text-primary': '#ffffff',
  '--text-secondary': '#c7c7c7',
  '--text-muted': '#707070',
  '--border': '#383838',
  '--border-subtle': '#2a2a2a',
  '--accent': '#92c5f9',
  '--accent-hover': '#b9dafc',
  '--success': '#87bb62',
  '--error': '#f0561d',
};

const LIGHT_STYLES = {
  '--color-background-primary': '#ffffff',
  '--color-background-secondary': '#f5f5f5',
  '--color-background-tertiary': '#e8e8e8',
  '--color-text-primary': '#1a1a1a',
  '--color-text-secondary': '#4a4a4a',
  '--color-text-tertiary': '#8a8a8a',
  '--color-border-primary': '#d4d4d4',
  '--color-border-secondary': '#e5e5e5',
  '--bg-primary': '#ffffff',
  '--bg-secondary': '#f5f5f5',
  '--bg-surface': '#e8e8e8',
  '--text-primary': '#1a1a1a',
  '--text-secondary': '#4a4a4a',
  '--text-muted': '#8a8a8a',
  '--border': '#d4d4d4',
  '--border-subtle': '#e5e5e5',
  '--accent': '#2563eb',
  '--accent-hover': '#1d4ed8',
  '--success': '#16a34a',
  '--error': '#dc2626',
};

export function McpAppRenderer({ resource, title, theme = 'dark', onAction }: Props) {
  const mimeType = resource.mimeType || 'text/html';

  const remoteDomTree = useMemo<RemoteDomNode | null>(() => {
    if (mimeType !== REMOTE_DOM_MIME) return null;
    try {
      return JSON.parse(resource.text || '{}');
    } catch {
      return null;
    }
  }, [mimeType, resource.text]);

  const hostContext = useMemo<McpUiHostContext>(() => ({
    theme: theme,
    styles: {
      variables: theme === 'light' ? LIGHT_STYLES : DARK_STYLES,
    },
  } as unknown as McpUiHostContext), [theme]);

  if (mimeType === REMOTE_DOM_MIME) {
    if (!remoteDomTree) {
      return (
        <div className="mcp-app-renderer">
          <div style={{ padding: 16, color: 'var(--error)' }}>
            Failed to parse Remote DOM content
          </div>
        </div>
      );
    }
    return (
      <div className="mcp-app-renderer mcp-remote-dom">
        <RemoteDomRenderer tree={remoteDomTree} onAction={onAction} />
      </div>
    );
  }

  return (
    <div className="mcp-app-renderer">
      <AppRenderer
        toolName={title || 'ui'}
        sandbox={{ url: sandboxUrl }}
        html={resource.text || ''}
        hostContext={hostContext}
        onMessage={async (params) => {
          const content = (params as Record<string, unknown>).content;
          if (Array.isArray(content)) {
            const textBlock = content.find(
              (b: Record<string, unknown>) => b.type === 'text'
            );
            if (textBlock && typeof textBlock.text === 'string' && onAction) {
              onAction(textBlock.text);
            }
          }
          return {};
        }}
        onError={(error) => {
          console.error('[McpAppRenderer]', error);
        }}
      />
    </div>
  );
}
