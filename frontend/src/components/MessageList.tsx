import { useEffect, useRef, useMemo } from 'react';
import { Message, ToolResponseContent } from '../types/message';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';
import type { McpUiTheme } from './McpAppRenderer';

interface Props {
  messages: Message[];
  onAction?: (text: string) => void;
  isThinking?: boolean;
  theme?: McpUiTheme;
}

/** Check if a user message contains only toolResponse blocks (no real user text) */
function isToolResponseMessage(msg: Message): boolean {
  return (
    msg.role === 'user' &&
    msg.content.length > 0 &&
    msg.content.every((c) => c.type === 'toolResponse')
  );
}

/** Find the previous visible (non-tool-response) message before the given index */
function findPrevVisible(messages: Message[], index: number): Message | null {
  for (let i = index - 1; i >= 0; i--) {
    if (!isToolResponseMessage(messages[i])) return messages[i];
  }
  return null;
}

/**
 * Build a set of (messageId, resourceUri) pairs that should be hidden
 * because a LATER message contains a resource with the same URI.
 * This allows update_editor to replace the previous editor in-place.
 */
function buildSuppressedResources(
  messages: Message[],
  toolResponseMap: Map<string, ToolResponseContent>
): Set<string> {
  // Collect all (messageId, uri) pairs in order
  const seen: { msgId: string; uri: string }[] = [];

  for (const msg of messages) {
    if (msg.role !== 'assistant') continue;
    for (const block of msg.content) {
      // Direct resource blocks
      if (block.type === 'resource' && block.uri) {
        seen.push({ msgId: msg.id, uri: block.uri });
      }
      // Resources inside tool responses
      if (block.type === 'toolRequest') {
        const resp = toolResponseMap.get(block.id);
        if (!resp) continue;
        for (const rb of resp.tool_result.content) {
          const uri = rb.resource?.uri;
          if (uri) seen.push({ msgId: msg.id, uri });
        }
      }
    }
  }

  // For each URI, only the LAST occurrence wins; suppress all earlier ones
  const latestByUri = new Map<string, string>(); // uri -> msgId of latest
  for (const entry of seen) {
    latestByUri.set(entry.uri, entry.msgId);
  }

  const suppressed = new Set<string>();
  for (const entry of seen) {
    if (latestByUri.get(entry.uri) !== entry.msgId) {
      // This message's resource with this URI is not the latest — suppress it
      suppressed.add(`${entry.msgId}::${entry.uri}`);
    }
  }

  return suppressed;
}

export function MessageList({ messages, onAction, isThinking, theme }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const toolResponseMap = useMemo(() => {
    const map = new Map<string, ToolResponseContent>();
    for (const msg of messages) {
      for (const block of msg.content) {
        if (block.type === 'toolResponse') {
          map.set(block.id, block);
        }
      }
    }
    return map;
  }, [messages]);

  const suppressedResources = useMemo(
    () => buildSuppressedResources(messages, toolResponseMap),
    [messages, toolResponseMap]
  );

  if (messages.length === 0 && !isThinking) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <h3>Start a conversation</h3>
          <p>Send a message to begin chatting with the AI assistant.</p>
        </div>
      </div>
    );
  }

  // Check if last visible message is already an assistant message with content
  const lastVisibleMsg = [...messages].reverse().find((m) => !isToolResponseMessage(m));
  const hasAssistantResponse =
    lastVisibleMsg?.role === 'assistant' && lastVisibleMsg.content.length > 0;
  const showThinking = isThinking && !hasAssistantResponse;

  return (
    <div className="message-list">
      {messages.map((msg, index) => {
        if (isToolResponseMessage(msg)) return null;

        if (msg.role === 'user') {
          return <UserMessage key={msg.id} message={msg} />;
        }

        const prevVisible = findPrevVisible(messages, index);
        const showAvatar = !prevVisible || prevVisible.role !== 'assistant';

        return (
          <AssistantMessage
            key={msg.id}
            message={msg}
            toolResponseMap={toolResponseMap}
            onAction={onAction}
            showAvatar={showAvatar}
            suppressedResources={suppressedResources}
            theme={theme}
          />
        );
      })}

      {showThinking && (
        <div className="thinking-indicator">
          <div className="message-avatar assistant-avatar">AI</div>
          <div className="thinking-text">
            Thinking
            <span className="thinking-dots">
              <span />
              <span />
              <span />
            </span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
