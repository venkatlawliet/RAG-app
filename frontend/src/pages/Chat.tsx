import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost, streamSSE } from "@/lib/api";
import { Button, Input } from "@/components/ui";

type Thread = {
  id: string;
  title: string | null;
  last_response_id: string | null;
  vector_store_id: string | null;
  created_at: string;
};

type Msg = { role: "user" | "assistant"; content: string };

export default function Chat() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [active, setActive] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiGet<Thread[]>("/api/chat/threads").then((t) => {
      setThreads(t);
      if (t[0]) setActive(t[0]);
    });
  }, []);

  useEffect(() => {
    setMessages([]);
  }, [active?.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function newThread() {
    const t = await apiPost<Thread>("/api/chat/threads", { title: "New chat" });
    setThreads((cur) => [t, ...cur]);
    setActive(t);
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!active || !input.trim() || streaming) return;
    const userText = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userText }, { role: "assistant", content: "" }]);
    setStreaming(true);
    try {
      for await (const evt of streamSSE(`/api/chat/threads/${active.id}/messages`, {
        content: userText,
      })) {
        if (evt.event === "delta" && evt.data?.text) {
          setMessages((m) => {
            const copy = m.slice();
            copy[copy.length - 1] = {
              role: "assistant",
              content: copy[copy.length - 1].content + evt.data.text,
            };
            return copy;
          });
        } else if (evt.event === "done") {
          setActive((a) => (a ? { ...a, last_response_id: evt.data?.response_id ?? a.last_response_id } : a));
        } else if (evt.event === "error") {
          setMessages((m) => [...m, { role: "assistant", content: `\n[error] ${evt.data?.message ?? ""}` }]);
        }
      }
    } catch (err: any) {
      setMessages((m) => [...m, { role: "assistant", content: `\n[error] ${err.message}` }]);
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="h-full flex">
      <aside className="w-64 border-r border-zinc-200 bg-white flex flex-col">
        <div className="p-3 border-b">
          <Button onClick={newThread} className="w-full">+ New chat</Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.map((t) => (
            <button
              key={t.id}
              onClick={() => setActive(t)}
              className={`w-full text-left px-3 py-2 text-sm border-b border-zinc-100 truncate ${
                active?.id === t.id ? "bg-zinc-100" : "hover:bg-zinc-50"
              }`}
            >
              {t.title || "Untitled"}
            </button>
          ))}
          {threads.length === 0 && <p className="p-3 text-xs text-zinc-500">No threads yet.</p>}
        </div>
      </aside>
      <section className="flex-1 flex flex-col min-w-0">
        {active ? (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`max-w-3xl whitespace-pre-wrap text-sm ${
                    m.role === "user" ? "ml-auto bg-zinc-900 text-white px-4 py-2 rounded-lg" : "mr-auto bg-white border px-4 py-2 rounded-lg"
                  }`}
                >
                  {m.content || (m.role === "assistant" && streaming ? "…" : "")}
                </div>
              ))}
              {messages.length === 0 && (
                <p className="text-sm text-zinc-500">Send a message to start. Files you've uploaded are searched automatically.</p>
              )}
            </div>
            <form onSubmit={send} className="border-t bg-white p-3 flex gap-2">
              <Input
                placeholder="Ask anything…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={streaming}
              />
              <Button type="submit" disabled={streaming || !input.trim()}>
                Send
              </Button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-zinc-500">
            Create a chat to begin.
          </div>
        )}
      </section>
    </div>
  );
}
