import type {
  ChatResponse,
  Collection,
  Conversation,
  IngestionJob,
  KnowledgeBase,
  KnowledgeBaseDetail,
  Page,
  ReelDetail,
  ReelListItem,
  ReelStats,
  UploadResponse,
} from "../types";

const BASE = "/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path.startsWith("http") ? path : `${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = (body as { detail?: string }).detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, unknown>) => {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
};

export interface ReelQuery {
  page?: number;
  page_size?: number;
  category?: string;
  creator?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
}

export const api = {
  // ingestion
  uploadExport: async (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/ingestion/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`${res.status}: ${(await res.json()).detail}`);
    return res.json();
  },
  startImport: (job_id: number, thread_id: string) =>
    http<IngestionJob>("/ingestion/import", {
      method: "POST",
      body: JSON.stringify({ job_id, thread_id }),
    }),
  jobs: () => http<IngestionJob[]>("/ingestion/jobs"),
  job: (id: number) => http<IngestionJob>(`/ingestion/jobs/${id}`),
  conversations: (job_id: number) => http<Conversation[]>(`/ingestion/conversations${qs({ job_id })}`),

  // reels
  reels: (q: ReelQuery = {}) => http<Page<ReelListItem>>(`/reels${qs(q as Record<string, unknown>)}`),
  reel: (id: number) => http<ReelDetail>(`/reels/${id}`),
  updateReel: (id: number, patch: Partial<ReelDetail>) =>
    http<ReelDetail>(`/reels/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  retryReel: (id: number) => http<unknown>(`/reels/${id}/retry`, { method: "POST" }),
  stats: () => http<ReelStats>("/reels/stats"),
  reelPdfUrl: (id: number) => `${BASE}/reels/${id}/pdf`,

  // search
  search: (q: ReelQuery & { q: string; mode: string }) =>
    http<Page<ReelListItem>>(`/search${qs(q as unknown as Record<string, unknown>)}`),

  // collections
  collections: () => http<Collection[]>("/collections"),
  createCollection: (name: string, color?: string, description?: string) =>
    http<Collection>("/collections", { method: "POST", body: JSON.stringify({ name, color, description }) }),
  addToCollection: (id: number, reel_ids: number[]) =>
    http<Collection>(`/collections/${id}/reels`, { method: "POST", body: JSON.stringify({ reel_ids }) }),
  deleteCollection: (id: number) => http<unknown>(`/collections/${id}`, { method: "DELETE" }),

  // knowledge bases
  knowledgeBases: () => http<KnowledgeBase[]>("/knowledge-bases"),
  knowledgeBase: (id: number) => http<KnowledgeBaseDetail>(`/knowledge-bases/${id}`),
  createKnowledgeBase: (payload: {
    name: string;
    description?: string;
    source_type: string;
    thread_id?: string;
    collection_id?: number;
    reel_ids?: number[];
    filter?: Record<string, unknown>;
  }) => http<KnowledgeBaseDetail>("/knowledge-bases", { method: "POST", body: JSON.stringify(payload) }),
  deleteKnowledgeBase: (id: number) => http<unknown>(`/knowledge-bases/${id}`, { method: "DELETE" }),

  // chat
  chat: (query: string, knowledge_base_id?: number, session_id?: number) =>
    http<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ query, knowledge_base_id, session_id }),
    }),

  // pdf export
  exportPdf: async (payload: Record<string, unknown>): Promise<Blob> => {
    const res = await fetch(`${BASE}/export/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`${res.status}: export failed`);
    return res.blob();
  },
};
