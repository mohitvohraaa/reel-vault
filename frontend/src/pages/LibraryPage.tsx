import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { ReelCard } from "../components/ReelCard";
import { EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { api, type ReelQuery } from "../services/api";
import { STATUS_META } from "../lib/utils";

const STATUS_OPTIONS = Object.keys(STATUS_META);

export default function LibraryPage() {
  const [filters, setFilters] = useState<ReelQuery>({ page: 1, page_size: 12, sort: "shared_at_desc" });
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const reels = useQuery({ queryKey: ["reels", filters], queryFn: () => api.reels(filters) });

  const set = (patch: Partial<ReelQuery>) => setFilters((f) => ({ ...f, ...patch, page: patch.page ?? 1 }));
  const totalPages = reels.data ? Math.max(1, Math.ceil(reels.data.total / (filters.page_size || 12))) : 1;

  return (
    <div>
      <PageHeader title="Reel Library" subtitle={reels.data ? `${reels.data.total} reels` : undefined} />

      <div className="card mb-5 grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
        <select className="input" value={filters.category || ""} onChange={(e) => set({ category: e.target.value || undefined })}>
          <option value="">All categories</option>
          {stats.data?.by_category.map((c) => (
            <option key={c.category} value={c.category}>
              {c.category} ({c.count})
            </option>
          ))}
        </select>
        <input
          className="input"
          placeholder="Creator username"
          value={filters.creator || ""}
          onChange={(e) => set({ creator: e.target.value || undefined })}
        />
        <select className="input" value={filters.status || ""} onChange={(e) => set({ status: e.target.value || undefined })}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {STATUS_META[s].label}
            </option>
          ))}
        </select>
        <input className="input" type="date" value={filters.date_from || ""} onChange={(e) => set({ date_from: e.target.value || undefined })} />
        <input className="input" type="date" value={filters.date_to || ""} onChange={(e) => set({ date_to: e.target.value || undefined })} />
      </div>

      {reels.isLoading ? (
        <Loading />
      ) : reels.error ? (
        <ErrorNote error={reels.error} />
      ) : reels.data && reels.data.items.length > 0 ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {reels.data.items.map((r) => (
              <ReelCard key={r.id} reel={r} />
            ))}
          </div>
          <div className="mt-6 flex items-center justify-center gap-4 text-sm">
            <button className="btn-ghost" disabled={(filters.page || 1) <= 1} onClick={() => set({ page: (filters.page || 1) - 1 })}>
              <ChevronLeft className="h-4 w-4" /> Prev
            </button>
            <span className="text-muted">
              Page {filters.page || 1} of {totalPages}
            </span>
            <button className="btn-ghost" disabled={(filters.page || 1) >= totalPages} onClick={() => set({ page: (filters.page || 1) + 1 })}>
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </>
      ) : (
        <EmptyState title="No reels match these filters" hint="Try clearing filters or importing more reels." />
      )}
    </div>
  );
}
