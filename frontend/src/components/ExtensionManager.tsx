import { useState } from 'react';
import { Plus, X, Server } from 'lucide-react';
import { ExtensionConfig } from '../types/extension';

interface Props {
  sessionId: string;
  extensions: ExtensionConfig[];
  onAdd: (config: ExtensionConfig) => void;
  onRemove: (name: string) => void;
}

export function ExtensionManager({ sessionId, extensions, onAdd, onRemove }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState<'stdio' | 'streamable_http'>('stdio');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cmd, setCmd] = useState('');
  const [args, setArgs] = useState('');
  const [uri, setUri] = useState('');

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

    // Reset form
    setName('');
    setDescription('');
    setCmd('');
    setArgs('');
    setUri('');
    setShowForm(false);
  };

  return (
    <div className="extension-manager">
      <div className="extension-header">
        <h3>
          <Server size={16} /> MCP Servers
        </h3>
        <button className="btn-icon" onClick={() => setShowForm(!showForm)} title="Add MCP Server">
          <Plus size={18} />
        </button>
      </div>

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
                <input value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder="npx" required />
              </div>
              <div className="form-group">
                <label>Arguments (space-separated)</label>
                <input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="@modelcontextprotocol/server-filesystem /tmp" />
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

      <div className="extension-list">
        {extensions.length === 0 && <p className="empty-text">No MCP servers connected</p>}
        {extensions.map((ext) => (
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
    </div>
  );
}
