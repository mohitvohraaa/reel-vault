import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { cn, STATUS_META } from "../lib/utils";

export function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] || { label: status, className: "bg-slate-500/15 text-slate-400" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", meta.className)}>
      {meta.label}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("animate-spin text-muted", className)} />;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-12 text-sm text-muted">
      <Spinner className="h-4 w-4" /> {label}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-14 text-center">
      <p className="text-base font-medium">{title}</p>
      {hint && <p className="max-w-md text-sm text-muted">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
      {msg}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}
