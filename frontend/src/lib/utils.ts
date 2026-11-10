import clsx, { type ClassValue } from "clsx";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export const STATUS_META: Record<string, { label: string; className: string }> = {
  discovered: { label: "Discovered", className: "bg-slate-500/15 text-slate-400" },
  metadata_extracted: { label: "Metadata", className: "bg-slate-500/15 text-slate-400" },
  downloading: { label: "Downloading", className: "bg-blue-500/15 text-blue-400" },
  transcribing: { label: "Transcribing", className: "bg-blue-500/15 text-blue-400" },
  summarizing: { label: "Summarizing", className: "bg-blue-500/15 text-blue-400" },
  embedding: { label: "Embedding", className: "bg-blue-500/15 text-blue-400" },
  completed: { label: "Completed", className: "bg-emerald-500/15 text-emerald-400" },
  media_unavailable: { label: "Media unavailable", className: "bg-amber-500/15 text-amber-500" },
  transcription_failed: { label: "Transcription failed", className: "bg-red-500/15 text-red-400" },
  summarization_failed: { label: "Summarization failed", className: "bg-red-500/15 text-red-400" },
  embedding_failed: { label: "Embedding failed", className: "bg-red-500/15 text-red-400" },
  insufficient_content: { label: "Insufficient content", className: "bg-amber-500/15 text-amber-500" },
};

export const IMPORTANCE_META: Record<string, string> = {
  high: "bg-red-500/15 text-red-400",
  medium: "bg-amber-500/15 text-amber-500",
  low: "bg-slate-500/15 text-slate-400",
};

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
