import { Session } from '../types/session';
import { Plus, Trash2, MessageSquare, PanelLeftClose } from 'lucide-react';

interface Props {
  sessions: Session[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onCollapse: () => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  onDelete,
  onCollapse,
}: Props) {
  return (
    <div className="session-sidebar">
      {/* Top bar — collapse + new chat */}
      <div className="sidebar-top-bar">
        <button className="btn-icon" onClick={onCollapse} title="Collapse sidebar">
          <PanelLeftClose size={18} />
        </button>
        <button className="btn-icon" onClick={onCreate} title="New Chat">
          <Plus size={20} />
        </button>
      </div>

      {/* Section label + divider */}
      <div className="sidebar-section-label">Recent Chats</div>
      <div className="sidebar-divider" />

      {/* Session list */}
      <div className="session-list">
        {sessions.length === 0 && (
          <p className="empty-text">No sessions yet. Create one!</p>
        )}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSelect(session.id)}
          >
            <MessageSquare size={16} />
            <span className="session-name">{session.name}</span>
            <button
              className="btn-icon btn-delete"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(session.id);
              }}
              title="Delete"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
