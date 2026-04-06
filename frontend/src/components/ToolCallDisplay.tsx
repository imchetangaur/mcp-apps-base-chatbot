import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  CheckCircle,
  XCircle,
  Loader,
} from 'lucide-react';
import { ToolRequestContent, ToolResponseContent } from '../types/message';

interface Props {
  request: ToolRequestContent;
  response?: ToolResponseContent;
}

export function ToolCallDisplay({ request, response }: Props) {
  const [expanded, setExpanded] = useState(false);

  const isLoading = !response;
  const isError = response?.tool_result.status === 'error';
  const resultBlocks = response?.tool_result.content || [];

  const textResult = resultBlocks
    .filter((b) => b.type === 'text')
    .map((b) => b.text || '')
    .join('\n');

  return (
    <div className="tool-call">
      <div className="tool-call-header" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <Wrench size={14} />
        <span className="tool-name">{request.tool_call.name}</span>
        {isLoading && <Loader size={14} className="spinner" />}
        {response && !isError && <CheckCircle size={14} className="tool-success" />}
        {isError && <XCircle size={14} className="tool-error-icon" />}
      </div>

      {expanded && (
        <div className="tool-call-details">
          <div className="tool-section">
            <strong>Arguments:</strong>
            <pre>{JSON.stringify(request.tool_call.arguments, null, 2)}</pre>
          </div>

          {response && (
            <div className="tool-section">
              <strong>{isError ? 'Error:' : 'Result:'}</strong>
              <pre>{textResult || '(success)'}</pre>
            </div>
          )}

          {isLoading && (
            <div className="tool-section tool-loading">
              <Loader size={16} className="spinner" />
              <span>Executing tool...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
