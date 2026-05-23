import {
  Message,
  ToolRequestContent,
  ToolResponseContent,
  ToolResultBlock,
  ResourceContent,
} from '../types/message';
import { ToolCallDisplay } from './ToolCallDisplay';
import { McpAppRenderer, type McpUiTheme } from './McpAppRenderer';
import ReactMarkdown from 'react-markdown';

interface Props {
  message: Message;
  toolResponseMap?: Map<string, ToolResponseContent>;
  onAction?: (text: string) => void;
  showAvatar?: boolean;
  suppressedResources?: Set<string>;
  theme?: McpUiTheme;
}

const REMOTE_DOM_MIME = 'application/vnd.mcp-ui.remote-dom';
const MCP_APP_MIME = 'text/html;profile=mcp-app';

function isRichContent(block: ToolResultBlock): boolean {
  if (block.type === 'resource' && block.resource) {
    const mime = block.mimeType || block.resource.mimeType || '';
    if (mime.includes('html') || mime === REMOTE_DOM_MIME || mime === MCP_APP_MIME) return true;
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

interface ExtractedResource {
  uri: string;
  mimeType: string;
  text?: string;
  blob?: string;
}

function extractResource(block: ToolResultBlock, toolName: string, index: number): ExtractedResource {
  const mime = block.mimeType || block.resource?.mimeType || 'text/html';
  const uri = block.resource?.uri || `ui://${toolName}/result-${index}`;
  if (block.type === 'resource' && block.resource) {
    return { uri, mimeType: mime, text: block.resource.text, blob: block.resource.blob };
  }
  return { uri, mimeType: mime, text: block.text || '' };
}

function isImageContent(block: ToolResultBlock): boolean {
  return block.type === 'image' && !!block.data;
}

function isRichResource(res: ResourceContent): boolean {
  const mime = res.mimeType || '';
  if (mime.includes('html') || mime === REMOTE_DOM_MIME || mime === MCP_APP_MIME) return true;
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
  theme,
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

  const toolRichItems: { resource: ExtractedResource; key: string; toolName: string }[] = [];
  const toolImageItems: { src: string; key: string }[] = [];
  for (const req of toolRequests) {
    const resp = toolResponseMap?.get(req.id);
    if (!resp) continue;
    for (let i = 0; i < resp.tool_result.content.length; i++) {
      const block = resp.tool_result.content[i];

      const uri = block.resource?.uri;
      if (uri && suppressedResources?.has(`${message.id}::${uri}`)) {
        continue;
      }

      if (isRichContent(block)) {
        toolRichItems.push({
          resource: extractResource(block, req.tool_call.name, i),
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
        {toolRequests.map((req) => (
          <ToolCallDisplay
            key={req.id}
            request={req}
            response={toolResponseMap?.get(req.id)}
          />
        ))}

        {textParts.length > 0 && (
          <div className="markdown-content">
            <ReactMarkdown>{textParts.join('\n')}</ReactMarkdown>
          </div>
        )}

        {resourceBlocks.map((res, i) => {
          const uri = res.uri;
          if (uri && suppressedResources?.has(`${message.id}::${uri}`)) return null;
          return isRichResource(res) && res.text ? (
            <div key={`res-${i}`} className="mcp-inline-content">
              <McpAppRenderer
                resource={{
                  uri: res.uri,
                  mimeType: res.mimeType,
                  text: res.text,
                  blob: res.blob,
                }}
                title={res.uri}
                theme={theme}
                onAction={onAction}
              />
            </div>
          ) : null;
        })}

        {toolRichItems.map((item) => (
          <div key={item.key} className="mcp-inline-content">
            <McpAppRenderer
              resource={item.resource}
              title={item.toolName}
              theme={theme}
              onAction={onAction}
            />
          </div>
        ))}

        {toolImageItems.map((item) => (
          <div key={item.key} className="mcp-inline-content">
            <img src={item.src} alt="Tool result" className="tool-result-image" />
          </div>
        ))}
      </div>
    </div>
  );
}
