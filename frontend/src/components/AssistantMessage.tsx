import {
  Message,
  ToolRequestContent,
  ToolResponseContent,
  ToolResultBlock,
  ResourceContent,
} from '../types/message';
import { ToolCallDisplay } from './ToolCallDisplay';
import { McpAppRenderer } from './McpAppRenderer';
import ReactMarkdown from 'react-markdown';

interface Props {
  message: Message;
  toolResponseMap?: Map<string, ToolResponseContent>;
  onAction?: (text: string) => void;
  /** Whether to show the avatar — only true for the first message in a consecutive AI group */
  showAvatar?: boolean;
  /** Set of "msgId::uri" keys whose rich content should be hidden (superseded by a later update) */
  suppressedResources?: Set<string>;
}

const REMOTE_DOM_MIME = 'application/vnd.mcp-ui.remote-dom';

/** Check if a result block contains renderable UI content (HTML or Remote DOM) */
function isRichContent(block: ToolResultBlock): boolean {
  if (block.type === 'resource' && block.resource) {
    const mime = block.mimeType || block.resource.mimeType || '';
    if (mime.includes('html') || mime === REMOTE_DOM_MIME) return true;
    const text = block.resource.text || '';
    if (text.trim().startsWith('<') && (text.includes('</') || text.includes('/>'))) return true;
  }
  if (block.type === 'text' && block.text) {
    const t = block.text.trim();
    if (
      (t.startsWith('<!DOCTYPE') || t.startsWith('<html') || t.startsWith('<div') || t.startsWith('<svg')) &&
      t.includes('</') &&
      t.length > 100
    ) {
      return true;
    }
  }
  return false;
}

/** Extract content string and mimeType from a result block */
function extractContent(block: ToolResultBlock): { content: string; mimeType: string } {
  const mime = block.mimeType || block.resource?.mimeType || 'text/html';
  if (block.type === 'resource' && block.resource?.text) {
    return { content: block.resource.text, mimeType: mime };
  }
  return { content: block.text || '', mimeType: mime };
}

function isImageContent(block: ToolResultBlock): boolean {
  return block.type === 'image' && !!block.data;
}

/** Check if a ResourceContent block contains renderable UI */
function isRichResource(res: ResourceContent): boolean {
  const mime = res.mimeType || '';
  if (mime.includes('html') || mime === REMOTE_DOM_MIME) return true;
  if (res.text) {
    const t = res.text.trim();
    if (
      (t.startsWith('<!DOCTYPE') || t.startsWith('<html') || t.startsWith('<div') || t.startsWith('{')) &&
      t.length > 50
    ) {
      return true;
    }
  }
  return false;
}

export function AssistantMessage({
  message,
  toolResponseMap,
  onAction,
  showAvatar = true,
  suppressedResources,
}: Props) {
  const toolRequests: ToolRequestContent[] = [];
  const textParts: string[] = [];
  const resourceBlocks: ResourceContent[] = [];

  for (const block of message.content) {
    switch (block.type) {
      case 'text':
        textParts.push(block.text);
        break;
      case 'toolRequest':
        toolRequests.push(block);
        break;
      case 'resource':
        resourceBlocks.push(block);
        break;
    }
  }

  // Collect rich content from tool responses (skip suppressed URIs)
  const toolRichItems: { content: string; mimeType: string; key: string; toolName: string }[] = [];
  const toolImageItems: { src: string; key: string }[] = [];
  for (const req of toolRequests) {
    const resp = toolResponseMap?.get(req.id);
    if (!resp) continue;
    for (let i = 0; i < resp.tool_result.content.length; i++) {
      const block = resp.tool_result.content[i];

      // Check if this resource is suppressed (superseded by a later update)
      const uri = block.resource?.uri;
      if (uri && suppressedResources?.has(`${message.id}::${uri}`)) {
        continue;
      }

      if (isRichContent(block)) {
        const { content, mimeType } = extractContent(block);
        toolRichItems.push({
          content,
          mimeType,
          toolName: req.tool_call.name,
          key: `${req.id}-rich-${i}`,
        });
      } else if (isImageContent(block)) {
        toolImageItems.push({
          src: `data:${block.mimeType || 'image/png'};base64,${block.data}`,
          key: `${req.id}-img-${i}`,
        });
      }
    }
  }

  // Check if ALL rich content in this message is suppressed (hide the entire message if empty)
  const hasVisibleContent =
    textParts.length > 0 ||
    toolRequests.length > 0 ||
    toolRichItems.length > 0 ||
    toolImageItems.length > 0 ||
    resourceBlocks.some((r) => {
      const uri = r.uri;
      if (uri && suppressedResources?.has(`${message.id}::${uri}`)) return false;
      return isRichResource(r) && r.text;
    });

  if (!hasVisibleContent) return null;

  return (
    <div className={`message assistant-message${showAvatar ? '' : ' no-avatar'}`}>
      {showAvatar ? (
        <div className="message-avatar assistant-avatar">AI</div>
      ) : (
        <div className="message-avatar-spacer" />
      )}
      <div className="message-body">
        {/* Tool calls — collapsed accordion */}
        {toolRequests.map((req) => (
          <ToolCallDisplay
            key={req.id}
            request={req}
            response={toolResponseMap?.get(req.id)}
          />
        ))}

        {/* AI text response */}
        {textParts.length > 0 && (
          <div className="markdown-content">
            <ReactMarkdown>{textParts.join('\n')}</ReactMarkdown>
          </div>
        )}

        {/* Resource content directly in the AI message */}
        {resourceBlocks.map((res, i) => {
          const uri = res.uri;
          if (uri && suppressedResources?.has(`${message.id}::${uri}`)) return null;
          return isRichResource(res) && res.text ? (
            <div key={`res-${i}`} className="mcp-inline-content">
              <McpAppRenderer
                content={res.text}
                mimeType={res.mimeType || 'text/html'}
                title={res.uri}
                onAction={onAction}
              />
            </div>
          ) : null;
        })}

        {/* Rich content from tool responses */}
        {toolRichItems.map((item) => (
          <div key={item.key} className="mcp-inline-content">
            <McpAppRenderer
              content={item.content}
              mimeType={item.mimeType}
              title={item.toolName}
              onAction={onAction}
            />
          </div>
        ))}

        {/* Images */}
        {toolImageItems.map((item) => (
          <div key={item.key} className="mcp-inline-content">
            <img src={item.src} alt="Tool result" className="tool-result-image" />
          </div>
        ))}
      </div>
    </div>
  );
}
