import type { Session } from "../types";

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
}

export default function Sidebar({ sessions, activeId, onSelect, onNewChat, onDelete }: Props) {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-neutral-800 bg-neutral-900">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full rounded-lg border border-neutral-700 px-3 py-2 text-left text-sm font-medium text-neutral-100 transition-colors hover:bg-neutral-800"
        >
          + New chat
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group mb-1 flex cursor-pointer items-center gap-1 rounded-lg px-2 py-2 text-sm ${
              s.id === activeId ? "bg-neutral-800 text-neutral-100" : "text-neutral-400 hover:bg-neutral-800/60"
            }`}
            onClick={() => onSelect(s.id)}
          >
            <span className="flex-1 truncate">{s.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
              className="px-1 text-neutral-500 opacity-0 hover:text-red-400 group-hover:opacity-100"
              title="Delete chat"
            >
              ×
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}
