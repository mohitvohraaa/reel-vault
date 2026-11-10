import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, ExternalLink, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorNote, Loading, StatusBadge } from "../components/ui";
import { api } from "../services/api";
import { formatDate } from "../lib/utils";

const DEFAULT_CATEGORIES = [
  "Technology", "Programming", "AI / Machine Learning", "Startups / Business", "Productivity",
  "Learning / Education", "Finance", "Fitness", "Travel", "Entertainment", "Lifestyle",
  "Interesting / Miscellaneous",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
      {children}
    </div>
  );
}

export default function ReelDetailPage() {
  const { id } = useParams();
  const reelId = Number(id);
  const qc = useQueryClient();
  const reel = useQuery({ queryKey: ["reel", reelId], queryFn: () => api.reel(reelId) });
  const [category, setCategory] = useState("");

  useEffect(() => {
    if (reel.data?.category) setCategory(reel.data.category);
  }, [reel.data?.category]);

  const retry = useMutation({
    mutationFn: () => api.retryReel(reelId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reel", reelId] }),
  });
  const save = useMutation({
    mutationFn: () => api.updateReel(reelId, { category }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reel", reelId] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  if (reel.isLoading) return <Loading />;
  if (reel.error) return <ErrorNote error={reel.error} />;
  if (!reel.data) return null;
  const r = reel.data;

  return (
    <div>
      <Link to="/library" className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> Back to library
      </Link>

      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{r.title || "Untitled Reel"}</h1>
          {r.one_liner && <p className="mt-1 max-w-2xl text-muted">{r.one_liner}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
            <StatusBadge status={r.processing_status} />
            {r.creator_username && <span>@{r.creator_username}</span>}
            <span>· shared {formatDate(r.shared_at)}</span>
            {r.language && <span>· {r.language}</span>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <a href={r.normalized_url} target="_blank" rel="noreferrer" className="btn-primary">
            <ExternalLink className="h-4 w-4" /> Open reel
          </a>
          <a href={api.reelPdfUrl(reelId)} target="_blank" rel="noreferrer" className="btn-ghost">
            <Download className="h-4 w-4" /> PDF
          </a>
          <button className="btn-ghost" onClick={() => retry.mutate()} disabled={retry.isPending}>
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        </div>
      </div>

      {r.processing_error && (
        <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-500">
          Note: {r.processing_error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          {r.summary && (
            <Section title="Summary">
              <p className="text-sm leading-relaxed">{r.summary}</p>
            </Section>
          )}
          {r.key_takeaways && r.key_takeaways.length > 0 && (
            <Section title="Key takeaways">
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {r.key_takeaways.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </Section>
          )}
          {r.actionable_insights && r.actionable_insights.length > 0 && (
            <Section title="Actionable insights">
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {r.actionable_insights.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </Section>
          )}
          <Section title="Transcript">
            {r.transcript ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">{r.transcript}</p>
            ) : (
              <p className="text-sm text-muted">No transcript available for this reel.</p>
            )}
          </Section>
        </div>

        <div className="space-y-5">
          <Section title="Categorization">
            <label className="mb-1 block text-xs text-muted">Category {r.category_source === "manual" && "(manual)"}</label>
            <input className="input mb-2" list="cats" value={category} onChange={(e) => setCategory(e.target.value)} />
            <datalist id="cats">
              {DEFAULT_CATEGORIES.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            <button className="btn-primary w-full justify-center" onClick={() => save.mutate()} disabled={save.isPending}>
              <Save className="h-4 w-4" /> Save category
            </button>
            {r.subcategories && r.subcategories.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {r.subcategories.map((s) => (
                  <span key={s} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            )}
          </Section>

          {r.entities && r.entities.length > 0 && (
            <Section title="Entities">
              <div className="flex flex-wrap gap-1.5">
                {r.entities.map((e) => (
                  <span key={e} className="tag">
                    {e}
                  </span>
                ))}
              </div>
            </Section>
          )}

          <Section title="Details">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Content type</dt>
                <dd>{r.content_type || "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Importance</dt>
                <dd>{r.importance || "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Duration</dt>
                <dd>{r.duration_sec ? `${Math.round(r.duration_sec)}s` : "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Shortcode</dt>
                <dd>{r.shortcode || "—"}</dd>
              </div>
            </dl>
          </Section>
        </div>
      </div>
    </div>
  );
}
