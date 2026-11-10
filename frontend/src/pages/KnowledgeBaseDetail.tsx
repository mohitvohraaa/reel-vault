import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Send } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorNote, Loading } from "../components/ui";
import { api } from "../services/api";
import { downloadBlob } from "../lib/utils";
import type { ChatMessage } from "../types";

export default function KnowledgeBaseDetail() {
  const { id } = useParams();
  const kbId = Number(id);
  const kb = useQuery({ queryKey: ["kb", kbId], queryFn: () => api.knowledgeBase(kbId) });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<number | undefined>();
  const [input, setInput] = useState("");

  const send = useMutation({
    mutationFn: (query: string) => api.chat(query, kbId, sessionId),
    onSuccess: (res) => {
      setSessionId(res.session_id);
      setMessages((m) => [...m, res.answer]);
    },
  });

  const exportPdf = useMutation({
    mutationFn: () => api.exportPdf({ knowledge_base_id: kbId }),
    onSuccess: (blob) => downloadBlob(blob, `knowledge-base-${kbId}.pdf`),
  });

  const submit = () => {
    const q = input.trim();
    if (!q) return;
    setMessages((m) => [...m, { id: Date.now(), role: "user", content: q }]);
    setInput("");
    send.mutate(q);
  };

  if (kb.isLoading) return <Loading />;
  if (kb.error) return <ErrorNote error={kb.error} />;
  if (!kb.data) return null;

  return (
    <div>
      <Link to="/knowledge-bases" className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> Knowledge bases
      </Link>

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{kb.data.name}</h1>
          <p className="mt-1 text-sm text-muted">
            <span className="chip mr-2 capitalize">{kb.data.source_type}</span>
            {kb.data.reel_count} reels in scope
          </p>
        </div>
        <button className="btn-ghost" onClick={() => exportPdf.mutate()} disabled={exportPdf.isPending}>
          <Download className="h-4 w-4" /> Export PDF
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Chat */}
        <div className="card flex h-[32rem] flex-col lg:col-span-2">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && (
              <p className="text-sm text-muted">
                Ask a question about the {kb.data.reel_count} reels in this knowledge base. Answers are grounded in the reels and cite their sources.
              </p>
            )}
            {messages.map((m) => (
              <div key={m.id} className={m.role === "user" ? "text-right" : ""}>
                <div
                  className={
                    m.role === "user"
                      ? "ml-auto inline-block max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-4 py-2 text-sm text-white"
                      : "inline-block max-w-[90%] rounded-2xl rounded-bl-sm bg-surface px-4 py-2 text-sm"
                  }
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                </div>
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {m.citations.map((c) => (
                      <Link key={c.reel_id} to={`/reels/${c.reel_id}`} className="chip hover:border-accent hover:text-accent">
                        #{c.reel_id} {c.title || "reel"}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {send.isPending && <p className="text-sm text-muted">Thinking…</p>}
            {send.error && <ErrorNote error={send.error} />}
          </div>
          <div className="flex items-center gap-2 border-t border-border p-3">
            <input
              className="input"
              placeholder="Ask about these reels…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <button className="btn-primary" onClick={submit} disabled={send.isPending}>
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Member reels */}
        <div className="card p-4">
          <h2 className="mb-3 text-sm font-semibold">Reels in scope</h2>
          <div className="max-h-[28rem] space-y-2 overflow-y-auto">
            {kb.data.reels.map((r) => (
              <Link key={r.id} to={`/reels/${r.id}`} className="block rounded-lg border border-border p-2.5 text-sm hover:border-accent">
                <div className="truncate font-medium">{r.title || r.caption || "Untitled"}</div>
                <div className="truncate text-xs text-muted">{r.category || "—"}</div>
              </Link>
            ))}
            {kb.data.reels.length === 0 && <p className="text-sm text-muted">No reels in this knowledge base.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
