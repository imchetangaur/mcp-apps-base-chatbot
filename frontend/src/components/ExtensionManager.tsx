import { useState } from 'react';
import { Plus, X, Server, Plug, Unplug, Loader, MessageSquare } from 'lucide-react';
import { ExtensionConfig } from '../types/extension';
import { PRESET_MCP_SERVERS } from '../config/mcpServers';

interface Props {
  sessionId: string;
  extensions: ExtensionConfig[];
  onAdd: (config: ExtensionConfig) => void;
  onRemove: (name: string) => void;
  onSampleQuery?: (text: string) => void;
}

export function ExtensionManager({ sessionId, extensions, onAdd, onRemove, onSampleQuery }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState<'stdio' | 'streamable_http'>('stdio');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cmd, setCmd] = useState('');
  const [args, setArgs] = useState('');
  const [uri, setUri] = useState('');
  const [connecting, setConnecting] = useState<Set<string>>(new Set());

  const connectedNames = new Set(extensions.map((e) => e.name));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    if (formType === 'stdio') {
      onAdd({
        type: 'stdio',
        name: name.trim(),
        description: description.trim(),
        cmd: cmd.trim(),
        args: args.trim() ? args.trim().split(' ') : [],
        envs: {},
      });
    } else {
      onAdd({
        type: 'streamable_http',
        name: name.trim(),
        description: description.trim(),
        uri: uri.trim(),
      });
    }

    setName('');
    setDescription('');
    setCmd('');
    setArgs('');
    setUri('');
    setShowForm(false);
  };

  const handlePresetToggle = async (config: ExtensionConfig) => {
    if (connectedNames.has(config.name)) {
      onRemove(config.name);
    } else {
      setConnecting((prev) => new Set(prev).add(config.name));
      try {
        await Promise.resolve(onAdd(config));
      } finally {
        setConnecting((prev) => {
          const next = new Set(prev);
          next.delete(config.name);
          return next;
        });
      }
    }
  };

  return (
    <div className="extension-manager">
      <div className="extension-header">
        <h3>
          <Server size={16} /> MCP Servers
        </h3>
        <button className="btn-icon" onClick={() => setShowForm(!showForm)} title="Add custom MCP Server">
          <Plus size={18} />
        </button>
      </div>

      {/* Preset servers */}
      <div className="preset-servers">
        {PRESET_MCP_SERVERS.map((preset) => {
          const isConnected = connectedNames.has(preset.config.name);
          const isConnecting = connecting.has(preset.config.name);
          return (
            <div key={preset.config.name} className={`preset-item ${isConnected ? 'connected' : ''}`}>
              <div className="preset-info">
                <span className="preset-name">{preset.config.name}</span>
                <span className="preset-desc">{preset.config.description}</span>
              </div>
              <button
                className={`btn-preset ${isConnected ? 'btn-disconnect' : 'btn-connect'}`}
                onClick={() => handlePresetToggle(preset.config)}
                disabled={isConnecting}
                title={isConnected ? 'Disconnect' : 'Connect'}
              >
                {isConnecting ? (
                  <Loader size={14} className="spinner" />
                ) : isConnected ? (
                  <Unplug size={14} />
                ) : (
                  <Plug size={14} />
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Sample queries for connected servers */}
      {onSampleQuery && PRESET_MCP_SERVERS.some((p) => connectedNames.has(p.config.name)) && (
        <div className="sample-queries">
          <div className="preset-label">
            <MessageSquare size={12} /> Try asking
          </div>
          {PRESET_MCP_SERVERS.filter((p) => connectedNames.has(p.config.name)).map((preset) =>
            preset.sampleQueries.map((q) => (
              <button
                key={`${preset.config.name}-${q}`}
                className="sample-query-chip"
                onClick={() => onSampleQuery(q)}
                title={`Server: ${preset.config.name}`}
              >
                {q}
              </button>
            ))
          )}
        </div>
      )}

      {showForm && (
        <form className="extension-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Type</label>
            <select value={formType} onChange={(e) => setFormType(e.target.value as any)}>
              <option value="stdio">Stdio (subprocess)</option>
              <option value="streamable_http">HTTP (remote)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="my-server" required />
          </div>
          <div className="form-group">
            <label>Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional description" />
          </div>
          {formType === 'stdio' ? (
            <>
              <div className="form-group">
                <label>Command</label>
                <input value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder="python3" required />
              </div>
              <div className="form-group">
                <label>Arguments (space-separated)</label>
                <input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="/path/to/server.py" />
              </div>
            </>
          ) : (
            <div className="form-group">
              <label>URL</label>
              <input value={uri} onChange={(e) => setUri(e.target.value)} placeholder="http://localhost:3001/mcp" required />
            </div>
          )}
          <div className="form-actions">
            <button type="submit" className="btn-primary">Add</button>
            <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {/* Custom (non-preset) connected servers */}
      {extensions.filter((e) => !PRESET_MCP_SERVERS.some((p) => p.config.name === e.name)).length > 0 && (
        <>
          <div className="preset-label" style={{ marginTop: '12px' }}>Custom</div>
          <div className="extension-list">
            {extensions
              .filter((e) => !PRESET_MCP_SERVERS.some((p) => p.config.name === e.name))
              .map((ext) => (
                <div key={ext.name} className="extension-item">
                  <Server size={14} />
                  <span className="extension-name">{ext.name}</span>
                  <span className="extension-type">{ext.type}</span>
                  <button className="btn-icon btn-delete" onClick={() => onRemove(ext.name)} title="Remove">
                    <X size={14} />
                  </button>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}
