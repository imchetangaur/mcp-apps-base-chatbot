export type Role = 'user' | 'assistant';

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolRequestContent {
  type: 'toolRequest';
  id: string;
  tool_call: ToolCall;
}

/** A single content block inside a tool result */
export interface ToolResultBlock {
  type: 'text' | 'image' | 'resource';
  text?: string;
  /** base64 image data */
  data?: string;
  mimeType?: string;
  /** Embedded resource (MCP resource with URI) */
  resource?: {
    uri: string;
    mimeType?: string;
    text?: string;
    blob?: string;
  };
}

export interface ToolResult {
  status: string;
  content: ToolResultBlock[];
}

export interface ToolResponseContent {
  type: 'toolResponse';
  id: string;
  tool_result: ToolResult;
}

/** Embedded resource content rendered inline in the AI response */
export interface ResourceContent {
  type: 'resource';
  uri: string;
  mimeType?: string;
  text?: string;
  blob?: string;
}

export type MessageContent = TextContent | ToolRequestContent | ToolResponseContent | ResourceContent;

export interface Message {
  id: string;
  role: Role;
  content: MessageContent[];
  created: number;
}
