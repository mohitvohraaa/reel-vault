import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { api } from "../services/api";

export default function KnowledgeBases() {
  const qc = useQueryClient();
  const kbs = useQuery({ queryKey: ["kbs"], queryFn: api.knowledgeBases });
  const collections = useQuery({ queryKey: ["collections"], queryFn: api.collections });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs });
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });

  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("filter");
  const [collectionId, setCollectionId] = useState<number | "">("");
  const [threadId, setThreadId] = useState("");
  const [category, setCategory] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api.createKnowledgeBase({
        name,
        source_type: sourceType,
        collection_id: sourceType === "collection" ? Number(collectionId) : undefined,
        thread_id: sourceType === "conversation" ? threadId : undefined,
        filter: sourceType === "filter" ? { category: category || undefined } : undefined,
      }),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({ queryKey: ["kbs"] });
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteKnowledgeBase(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kbs"] }),
  });

  const importedThreads = (jobs.data || [])
    .filter((j) => j.conversation_thread_id)
    .map((j) => ({ id: j.conversation_thread_id!, name: j.conversation_name || j.conversation_thread_id! }));

  return (
    <div>
      <PageHeader title="Knowledge Bases" subtitle="Scope a set of reels, then chat with them. Grounded answers cite the reels they came from." />

      <div className="card mb-5 p-5">
        <h2 className="mb-3 text-sm font-semibold">Create a knowledge base</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input className="input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="input" value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="filter">From a category</option>
            <option value="collection">From a collection</option>
            <option value="conversation">From a conversation</option>
          </select>

          {sourceType === "filter" && (
            <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {stats.data?.by_category.map((c) => (
                <option key={c.category} value={c.category}>
                  {c.category} ({c.count})
                </option>
              ))}
            </select>
          )}
          {sourceType === "collection" && (
            <select className="input" value={collectionId} onChange={(e) => setCollectionId(Number(e.target.value))}>
              <option value="">Select collection…</option>
              {collections.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.reel_count})
                </option>
              ))}
            </select>
          )}
          {sourceType === "conversation" && (
            <select className="input" value={threadId} onChange={(e) => setThreadId(e.target.value)}>
              <option value="">Select conversation…</option>
              {importedThreads.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          className="btn-primary mt-4"
          disabled={!name.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          <Plus className="h-4 w-4" /> Create knowledge base
        </button>
        {create.error && <div className="mt-3"><ErrorNote error={create.error} /></div>}
      </div>

      {kbs.isLoading ? (
        <Loading />
      ) : kbs.data && kbs.data.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {kbs.data.map((kb) => (
            <div key={kb.id} className="card flex flex-col p-4">
              <div className="mb-2 flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-accent" />
                  <Link to={`/knowledge-bases/${kb.id}`} className="text-sm font-semibold hover:text-accent">
                    {kb.name}
                  </Link>
                </div>
                <button className="text-red-400" onClick={() => remove.mutate(kb.id)} title="Delete">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="mb-3 flex items-center gap-2 text-xs text-muted">
                <span className="chip capitalize">{kb.source_type}</span>
                <span>{kb.reel_count} reels</span>
              </div>
              <Link to={`/knowledge-bases/${kb.id}`} className="btn-ghost mt-auto justify-center py-1.5 text-xs">
                Open & chat
              </Link>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No knowledge bases yet" hint="Create one from a category, collection, or conversation to start chatting." />
      )}
    </div>
  );
}
