import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Film, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { ReelCard } from "../components/ReelCard";
import { EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { api } from "../services/api";

function StatCard({ icon: Icon, label, value, tint }: { icon: typeof Film; label: string; value: number; tint: string }) {
  return (
    <div className="card flex items-center gap-4 p-4">
      <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tint}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-2xl font-semibold">{value}</div>
        <div className="text-xs text-muted">{label}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const recent = useQuery({ queryKey: ["reels", "recent"], queryFn: () => api.reels({ page: 1, page_size: 6 }) });

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Your Instagram reel knowledge base at a glance." />

      {stats.isLoading ? (
        <Loading />
      ) : stats.error ? (
        <ErrorNote error={stats.error} />
      ) : stats.data ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard icon={Film} label="Total reels" value={stats.data.total} tint="bg-accent/15 text-accent" />
            <StatCard icon={CheckCircle2} label="Completed" value={stats.data.completed} tint="bg-emerald-500/15 text-emerald-400" />
            <StatCard icon={Clock} label="Pending" value={stats.data.pending} tint="bg-blue-500/15 text-blue-400" />
            <StatCard icon={XCircle} label="Needs attention" value={stats.data.failed} tint="bg-amber-500/15 text-amber-500" />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <div className="card p-5 lg:col-span-1">
              <h2 className="mb-4 text-sm font-semibold">Category distribution</h2>
              {stats.data.by_category.length === 0 ? (
                <p className="text-sm text-muted">No categorized reels yet.</p>
              ) : (
                <div className="space-y-3">
                  {stats.data.by_category.slice(0, 8).map((c) => {
                    const pct = stats.data!.total ? Math.round((c.count / stats.data!.total) * 100) : 0;
                    return (
                      <div key={c.category}>
                        <div className="mb-1 flex justify-between text-xs">
                          <span className="truncate">{c.category}</span>
                          <span className="text-muted">{c.count}</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-border">
                          <div className="h-1.5 rounded-full bg-accent" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="lg:col-span-2">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Recently shared</h2>
                <Link to="/library" className="text-xs text-accent hover:underline">
                  View all
                </Link>
              </div>
              {recent.isLoading ? (
                <Loading />
              ) : recent.data && recent.data.items.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {recent.data.items.map((r) => (
                    <ReelCard key={r.id} reel={r} />
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No reels yet"
                  hint="Import an Instagram data export to get started."
                  action={
                    <Link to="/import" className="btn-primary mt-2">
                      Import export
                    </Link>
                  }
                />
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
