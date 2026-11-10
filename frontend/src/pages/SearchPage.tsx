import { useQuery } from "@tanstack/react-query";
import { Search as SearchIcon } from "lucide-react";
import { useState } from "react";
import { ReelCard } from "../components/ReelCard";
import { EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { api } from "../services/api";
import { cn } from "../lib/utils";

const MODES = [
  { key: "keyword", label: "Keyword" },
  { key: "semantic", label: "Semantic" },
  { key: "hybrid", label: "Hybrid" },
];

export default function SearchPage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");

  const results = useQuery({
    queryKey: ["search", query, mode],
    queryFn: () => api.search({ q: query, mode, page: 1, page_size: 24 }),
    enabled: query.trim().length > 0,
  });

  return (
    <div>
      <PageHeader title="Search" subtitle="Find reels by words or concepts from their transcript and summary." />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(input);
        }}
        className="card mb-5 flex flex-col gap-3 p-4 sm:flex-row sm:items-center"
      >
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="input pl-9"
            placeholder="e.g. how to build AI agents"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>
        <div className="flex rounded-lg border border-border p-0.5">
          {MODES.map((m) => (
            <button
              type="button"
              key={m.key}
              onClick={() => setMode(m.key)}
              className={cn("rounded-md px-3 py-1.5 text-xs font-medium", mode === m.key ? "bg-accent text-white" : "text-muted")}
            >
              {m.label}
            </button>
          ))}
        </div>
        <button type="submit" className="btn-primary justify-center">
          Search
        </button>
      </form>

      {!query ? (
        <EmptyState title="Start typing to search" hint="Semantic search uses embeddings; keyword uses full-text search." />
      ) : results.isLoading ? (
        <Loading label="Searching…" />
      ) : results.error ? (
        <ErrorNote error={results.error} />
      ) : results.data && results.data.items.length > 0 ? (
        <>
          <p className="mb-3 text-sm text-muted">{results.data.total} results for “{query}”</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {results.data.items.map((r) => (
              <ReelCard key={r.id} reel={r} />
            ))}
          </div>
        </>
      ) : (
        <EmptyState title="No results" hint="Try a different query or search mode." />
      )}
    </div>
  );
}
