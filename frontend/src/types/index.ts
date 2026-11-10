export interface ReelListItem {
  id: number;
  reel_url: string;
  normalized_url: string;
  shortcode?: string | null;
  creator_username?: string | null;
  caption?: string | null;
  thumbnail_url?: string | null;
  shared_at?: string | null;
  title?: string | null;
  one_liner?: string | null;
  category?: string | null;
  subcategories?: string[] | null;
  content_type?: string | null;
  importance?: string | null;
  language?: string | null;
  processing_status: string;
  created_at?: string | null;
}

export interface ReelDetail extends ReelListItem {
  summary?: string | null;
  key_takeaways?: string[] | null;
  entities?: string[] | null;
  actionable_insights?: string[] | null;
  transcript?: string | null;
  transcript_language?: string | null;
  transcript_segments?: { start: number; end: number; text: string }[] | null;
  duration_sec?: number | null;
  processing_error?: string | null;
  category_source?: string | null;
  original_message_id?: string | null;
  ingestion_job_id?: number | null;
  updated_at?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface ReelStats {
  total: number;
  completed: number;
  pending: number;
  failed: number;
  by_category: CategoryCount[];
  by_status: Record<string, number>;
}

export interface Conversation {
  thread_id: string;
  title?: string | null;
  participants: string[];
  message_count: number;
  reel_count: number;
}

export interface IngestionJob {
  id: number;
  source_filename?: string | null;
  conversation_name?: string | null;
  conversation_thread_id?: string | null;
  status: string;
  total_conversations: number;
  total_messages: number;
  reels_found: number;
  reels_unique: number;
  duplicates_skipped: number;
  unsupported: number;
  parse_errors: number;
  reels_processed: number;
  errors?: unknown[] | null;
  report?: Record<string, unknown> | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface UploadResponse {
  job_id: number;
  status: string;
  conversations: Conversation[];
}

export interface Collection {
  id: number;
  name: string;
  slug: string;
  color?: string | null;
  description?: string | null;
  created_at?: string | null;
  reel_count: number;
}

export interface KnowledgeBase {
  id: number;
  name: string;
  description?: string | null;
  source_type: string;
  source_ref?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
  reel_count: number;
}

export interface KnowledgeBaseDetail extends KnowledgeBase {
  reels: ReelListItem[];
}

export interface Citation {
  reel_id: number;
  title?: string | null;
  url: string;
  snippet: string;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  citations?: Citation[] | null;
  created_at?: string | null;
}

export interface ChatResponse {
  session_id: number;
  answer: ChatMessage;
}
