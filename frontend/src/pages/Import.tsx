import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, MessageSquare } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorNote, PageHeader } from "../components/ui";
import { api } from "../services/api";
import { cn } from "../lib/utils";
import type { Conversation } from "../types";

export default function ImportPage() {
  const [jobId, setJobId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [importedJobId, setImportedJobId] = useState<number | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadExport(file),
    onSuccess: (res) => {
      setJobId(res.job_id);
      setConversations(res.conversations);
      setSelected(res.conversations[0]?.thread_id ?? null);
      setImportedJobId(null);
    },
  });

  const startImport = useMutation({
    mutationFn: () => api.startImport(jobId!, selected!),
    onSuccess: (job) => setImportedJobId(job.id),
  });

  // Poll job progress after import starts.
  const job = useQuery({
    queryKey: ["job", importedJobId],
    queryFn: () => api.job(importedJobId!),
    enabled: importedJobId != null,
    refetchInterval: (q) => (q.state.data && q.state.data.status === "completed" ? false : 1500),
  });

  const report = job.data?.report as Record<string, unknown> | undefined;

  return (
    <div>
      <PageHeader title="Import" subtitle="Upload your Instagram data export and import a conversation's shared reels." />

      {/* Step 1: upload */}
      <div className="card mb-5 p-6">
        <h2 className="mb-1 text-sm font-semibold">1. Upload export</h2>
        <p className="mb-4 text-sm text-muted">
          Accepts the Instagram data export as a <code>.zip</code> or a single <code>.json</code> messages file.
        </p>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-surface px-6 py-10 text-center hover:border-accent">
          <FileUp className="h-7 w-7 text-muted" />
          <span className="text-sm font-medium">Choose a .zip or .json file</span>
          <span className="text-xs text-muted">Your DM export, exported from Instagram</span>
          <input
            type="file"
            accept=".zip,.json,application/zip,application/json"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])}
          />
        </label>
        {upload.isPending && (
          <p className="mt-3 flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Parsing export…
          </p>
        )}
        {upload.error && <div className="mt-3"><ErrorNote error={upload.error} /></div>}
      </div>

      {/* Step 2: select conversation */}
      {conversations.length > 0 && (
        <div className="card mb-5 p-6">
          <h2 className="mb-1 text-sm font-semibold">2. Select the conversation to import</h2>
          <p className="mb-4 text-sm text-muted">Pick the thread where you share reels (usually your alt account — the one with the most reels).</p>
          <div className="space-y-2">
            {conversations.map((c) => (
              <button
                key={c.thread_id}
                onClick={() => setSelected(c.thread_id)}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-lg border px-4 py-3 text-left transition-colors",
                  selected === c.thread_id ? "border-accent bg-accent/5" : "border-border hover:bg-bg"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <MessageSquare className="h-4 w-4 shrink-0 text-muted" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{c.title || c.thread_id}</div>
                    <div className="truncate text-xs text-muted">{c.participants.join(", ") || "—"}</div>
                  </div>
                </div>
                <div className="shrink-0 text-right text-xs text-muted">
                  <div className="font-semibold text-accent">{c.reel_count} reels</div>
                  <div>{c.message_count} messages</div>
                </div>
              </button>
            ))}
          </div>
          <button className="btn-primary mt-4" disabled={!selected || startImport.isPending} onClick={() => startImport.mutate()}>
            {startImport.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Import selected conversation
          </button>
          {startImport.error && <div className="mt-3"><ErrorNote error={startImport.error} /></div>}
        </div>
      )}

      {/* Step 3: progress + report */}
      {importedJobId != null && job.data && (
        <div className="card p-6">
          <h2 className="mb-1 text-sm font-semibold">3. Import progress</h2>
          <div className="mb-4 flex items-center gap-2 text-sm">
            <span className="chip capitalize">{job.data.status}</span>
            <span className="text-muted">
              {job.data.reels_processed} / {job.data.reels_unique} reels processed
            </span>
            {job.data.status !== "completed" && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
          </div>

          {report && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {[
                ["Messages scanned", report.messages_scanned],
                ["Reel URLs discovered", report.reel_urls_discovered],
                ["Unique reels", report.unique_reels_in_conversation],
                ["New reels imported", report.new_reels_imported],
                ["Duplicates skipped", report.duplicates_skipped_within_conversation],
                ["Already in vault", report.already_in_vault_skipped],
                ["Unsupported", report.unsupported_messages],
                ["Parse errors", Array.isArray(report.parse_errors) ? report.parse_errors.length : 0],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg border border-border bg-surface p-3">
                  <div className="text-xl font-semibold">{String(value ?? 0)}</div>
                  <div className="text-xs text-muted">{String(label)}</div>
                </div>
              ))}
            </div>
          )}

          <Link to="/library" className="btn-primary mt-5">
            View imported reels
          </Link>
        </div>
      )}
    </div>
  );
}
