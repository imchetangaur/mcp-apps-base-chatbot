import React, { useCallback, createElement } from 'react';

/**
 * RemoteDomRenderer — renders a JSON component tree as native React elements.
 *
 * This implements the Remote DOM pattern for MCP-UI:
 * Instead of rendering HTML in a sandboxed iframe, the MCP server returns
 * a JSON description of the UI component tree. The host renders it natively
 * using React components that inherit the host's theme and styling.
 *
 * Benefits over iframe rendering:
 * - Native theming (inherits dark/light theme)
 * - Direct click handlers (no postMessage chain)
 * - No iframe overhead
 * - Seamless visual integration
 *
 * The JSON format follows Remote DOM serialization:
 * {
 *   "type": "div",
 *   "props": { "style": {...}, "className": "..." },
 *   "children": [...],
 *   "action": "optional action text sent on click"
 * }
 */

/** A node in the Remote DOM component tree */
export interface RemoteDomNode {
  type: string; // HTML tag or custom component name
  props?: Record<string, unknown>;
  children?: (RemoteDomNode | string)[];
  /** If set, clicking this node sends this text as a chat action */
  action?: string;
}

interface Props {
  /** JSON component tree from MCP server */
  tree: RemoteDomNode;
  /** Called when user interacts with a node that has an action */
  onAction?: (text: string) => void;
}

/** Map of supported element types to their rendered styles */
const THEME = {
  card: {
    background: 'transparent',
    borderRadius: '12px',
    overflow: 'hidden',
    border: 'none',
    cursor: 'pointer',
    transition: 'transform 0.2s',
  },
  'card:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
    gap: '16px',
  },
  heading: {
    color: 'var(--text-primary)',
    marginBottom: '16px',
    fontSize: '20px',
    fontWeight: '600' as const,
  },
  badge: {
    background: 'var(--accent)',
    color: 'white',
    padding: '3px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: '600' as const,
  },
  price: {
    fontSize: '22px',
    fontWeight: '800' as const,
    color: 'var(--accent)',
  },
  button: {
    background: 'var(--accent)',
    color: 'white',
    border: 'none',
    padding: '8px 20px',
    borderRadius: 'var(--radius)',
    fontSize: '13px',
    fontWeight: '600' as const,
    cursor: 'pointer',
  },
  description: {
    color: 'var(--text-secondary)',
    fontSize: '13px',
    lineHeight: '1.5',
    margin: '6px 0',
  },
  subtitle: {
    color: 'var(--text-muted)',
    fontSize: '13px',
  },
};

function renderNode(
  node: RemoteDomNode | string,
  onAction: ((text: string) => void) | undefined,
  key: string | number
): React.ReactNode {
  if (typeof node === 'string') {
    return node;
  }

  const { type, props = {}, children = [], action } = node;

  // Merge theme styles with inline styles
  const themeStyle = THEME[type as keyof typeof THEME];
  const inlineStyle = (props.style as Record<string, unknown>) || {};
  const mergedStyle = themeStyle
    ? { ...themeStyle, ...inlineStyle }
    : inlineStyle;

  // Build React props
  const reactProps: Record<string, unknown> = {
    key,
    style: Object.keys(mergedStyle).length > 0 ? mergedStyle : undefined,
    className: props.className as string | undefined,
  };

  // Copy allowed props
  if (props.src) reactProps.src = props.src;
  if (props.alt) reactProps.alt = props.alt;
  if (props.href) reactProps.href = props.href;
  if (props.target) reactProps.target = props.target;

  // Add click handler for actionable nodes
  if (action && onAction) {
    reactProps.onClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      onAction(action);
    };
    reactProps.role = 'button';
    reactProps.tabIndex = 0;
  }

  // Map custom types to HTML elements
  const tagMap: Record<string, string> = {
    card: 'div',
    grid: 'div',
    heading: 'h2',
    badge: 'span',
    price: 'span',
    description: 'p',
    subtitle: 'p',
    button: 'button',
    text: 'span',
    row: 'div',
    col: 'div',
    spacer: 'div',
  };

  const htmlTag = tagMap[type] || type;

  // Render children recursively
  const renderedChildren = children.map((child, i) =>
    renderNode(child, onAction, i)
  );

  return createElement(
    htmlTag,
    reactProps,
    renderedChildren.length > 0 ? renderedChildren : undefined
  );
}

export function RemoteDomRenderer({ tree, onAction }: Props) {
  const handleAction = useCallback(
    (text: string) => {
      onAction?.(text);
    },
    [onAction]
  );

  return (
    <div className="remote-dom-root">
      {renderNode(tree, handleAction, 'root')}
    </div>
  );
}
