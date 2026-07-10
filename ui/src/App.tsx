import { useCallback, useEffect, useRef, useState } from "react";
import { createSession, deleteSession, listSessions } from "./api";
import ChatWindow from "./components/ChatWindow";
import Sidebar from "./components/Sidebar";
import type { Session } from "./types";

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const didInit = useRef(false);

  const refreshSessions = useCallback(async () => {
    const list = await listSessions();
    setSessions(list);
    return list;
  }, []);

  const handleNewChat = useCallback(async () => {
    const session = await createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    setActiveId((prev) => (prev === id ? null : prev));
  }, []);

  useEffect(() => {
    // React StrictMode double-invokes effects in dev, which would otherwise
    // fire this init logic twice and create two "New chat" sessions.
    if (didInit.current) return;
    didInit.current = true;

    (async () => {
      try {
        const list = await refreshSessions();
        if (list.length > 0) {
          setActiveId(list[0].id);
        } else {
          await handleNewChat();
        }
      } catch {
        setError("Can't reach the agent backend. Is it running on http://localhost:8000?");
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshSessions, handleNewChat]);

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-950 px-6 text-center text-red-400">
        {error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-950 text-neutral-400">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-neutral-950 text-neutral-100">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
      />
      {activeId ? (
        <ChatWindow key={activeId} sessionId={activeId} onActivity={refreshSessions} />
      ) : (
        <div className="flex flex-1 items-center justify-center text-neutral-500">Select or start a chat</div>
      )}
    </div>
  );
}
