import { ExternalLink, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { cn, formatDate, IMPORTANCE_META } from "../lib/utils";
import type { ReelListItem } from "../types";
import { StatusBadge } from "./ui";

export function ReelCard({ reel }: { reel: ReelListItem }) {
  return (
    <div className="card flex flex-col p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <Link to={`/reels/${reel.id}`} className="text-sm font-semibold leading-snug hover:text-accent">
          {reel.title || reel.caption || "Untitled Reel"}
        </Link>
        {reel.importance && (
          <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase", IMPORTANCE_META[reel.importance])}>
            {reel.importance}
          </span>
        )}
      </div>

      {reel.one_liner && <p className="mb-3 line-clamp-2 text-sm text-muted">{reel.one_liner}</p>}

      <div className="mb-3 flex flex-wrap gap-1.5">
        {reel.category && <span className="tag">{reel.category}</span>}
        {(reel.subcategories || []).slice(0, 3).map((s) => (
          <span key={s} className="chip">
            {s}
          </span>
        ))}
      </div>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted">
        <div className="flex min-w-0 flex-col">
          <span className="truncate">{reel.creator_username ? `@${reel.creator_username}` : "unknown creator"}</span>
          <span>{formatDate(reel.shared_at)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={reel.processing_status} />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Link to={`/reels/${reel.id}`} className="btn-ghost flex-1 justify-center py-1.5 text-xs">
          <FileText className="h-3.5 w-3.5" /> Details
        </Link>
        <a
          href={reel.normalized_url}
          target="_blank"
          rel="noreferrer"
          className="btn-ghost justify-center py-1.5 text-xs"
          title="Open original reel"
        >
          <ExternalLink className="h-3.5 w-3.5" /> Open
        </a>
      </div>
    </div>
  );
}
