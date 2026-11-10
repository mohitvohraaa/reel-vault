import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { api } from "../services/api";

export default function Collections() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [color, setColor] = useState("#4f46e5");
  const collections = useQuery({ queryKey: ["collections"], queryFn: api.collections });

  const create = useMutation({
    mutationFn: () => api.createCollection(name, color),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteCollection(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });

  return (
    <div>
      <PageHeader title="Collections" subtitle="Group reels into custom collections. Build a knowledge base from any collection." />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
        className="card mb-5 flex flex-col gap-3 p-4 sm:flex-row sm:items-center"
      >
        <input className="input flex-1" placeholder="New collection name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="h-9 w-14 cursor-pointer rounded border border-border bg-surface" type="color" value={color} onChange={(e) => setColor(e.target.value)} />
        <button className="btn-primary justify-center" type="submit" disabled={create.isPending || !name.trim()}>
          <FolderPlus className="h-4 w-4" /> Create
        </button>
      </form>
      {create.error && <div className="mb-4"><ErrorNote error={create.error} /></div>}

      {collections.isLoading ? (
        <Loading />
      ) : collections.data && collections.data.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {collections.data.map((c) => (
            <div key={c.id} className="card flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <span className="h-8 w-8 rounded-lg" style={{ backgroundColor: c.color || "#4f46e5" }} />
                <div>
                  <div className="text-sm font-medium">{c.name}</div>
                  <div className="text-xs text-muted">{c.reel_count} reels</div>
                </div>
              </div>
              <button className="btn-ghost p-2 text-red-400" onClick={() => remove.mutate(c.id)} title="Delete">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No collections yet" hint="Create a collection to organize reels by theme or project." />
      )}
    </div>
  );
}
